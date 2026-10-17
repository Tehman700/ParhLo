"""Reader memory, layer 1 and 2: explicit profile (topic weights, entities) + interest anchors (embeddings)."""

import httpx
from pydantic import BaseModel, Field

from app.core.database import db
from app.parhlo.embed import embed_texts
from app.parhlo.topics import TOPICS, topic_text
from app.services.llm import get_llm

MAX_ANCHORS = 80


class Swipe(BaseModel):
    article_id: int
    liked: bool


class OnboardingIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    city: str = "Lahore"
    reading_minutes: int = Field(default=10, ge=3, le=30)
    region_mix: float = Field(default=0.5, ge=0, le=1)
    topics: list[str] = Field(min_length=1)
    entities: list[str] = []
    about: str | None = None
    swipes: list[Swipe] = []


class AboutExtraction(BaseModel):
    entities: list[str] = Field(default=[], description="Specific people, teams, companies, places to follow")
    interests: list[str] = Field(default=[], description="Short interest phrases, e.g. 'startup funding in Pakistan'")
    topics: list[str] = Field(default=[], description="Matching topic slugs from the given list")


async def geocode(city: str) -> tuple[float, float] | None:
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": city, "count": 1})
            res = (r.json().get("results") or [None])[0]
            return (res["latitude"], res["longitude"]) if res else None
    except Exception:
        return None


async def extract_about(about: str) -> AboutExtraction:
    prompt = (
        "Extract what this news reader cares about. Only use what the text says.\n"
        f"Topic slugs: {', '.join(TOPICS)}\n\nReader: {about}"
    )
    try:
        return await get_llm().json([{"role": "user", "content": prompt}], schema=AboutExtraction,
                                    reasoning_effort="minimal")
    except Exception:
        return AboutExtraction()


def add_anchors(conn, user_id, rows: list[tuple[str, str, float, object, int | None]]) -> None:
    """rows: (label, kind, weight, embedding, article_id). Merges near-duplicates by label."""
    for label, kind, weight, emb, article_id in rows:
        existing = conn.execute(
            "select id, weight from interest_anchors where user_id = %s and lower(label) = lower(%s)",
            (user_id, label),
        ).fetchone()
        if existing:
            conn.execute("update interest_anchors set weight = %s where id = %s",
                         (max(-1.5, min(1.5, existing["weight"] + weight * 0.5)), existing["id"]))
        else:
            conn.execute(
                "insert into interest_anchors (user_id, label, kind, weight, article_id, embedding) "
                "values (%s,%s,%s,%s,%s,%s)", (user_id, label, kind, weight, article_id, emb))
    # Keep memory bounded: drop the weakest anchors beyond the cap.
    conn.execute(
        """delete from interest_anchors where id in (
             select id from interest_anchors where user_id = %s order by abs(weight) desc offset %s)""",
        (user_id, MAX_ANCHORS))


async def onboard(user: dict, data: OnboardingIn) -> dict:
    topics = [t for t in data.topics if t in TOPICS]
    extraction = await extract_about(data.about) if data.about else AboutExtraction()
    entities = list(dict.fromkeys([*data.entities, *extraction.entities]))[:20]
    topics += [t for t in extraction.topics if t in TOPICS and t not in topics]

    weights = {slug: 0.1 for slug in TOPICS}
    weights.update({slug: 0.8 for slug in topics})

    # Anchors: chosen topics, followed entities, free-text interests, swiped headlines.
    texts = [topic_text(t) for t in topics] + entities + extraction.interests
    labels = [(TOPICS[t]["label"], "onboarding", 1.0) for t in topics] + \
             [(e, "entity", 0.9) for e in entities] + [(i, "onboarding", 0.8) for i in extraction.interests]
    vectors = await embed_texts(texts) if texts else []
    rows = [(lbl, kind, w, vec, None) for (lbl, kind, w), vec in zip(labels, vectors)]

    with db() as conn:
        if data.swipes:
            arts = {a["id"]: a for a in conn.execute(
                "select id, title, topics, embedding from articles where id = any(%s)",
                ([s.article_id for s in data.swipes],))}
            for s in data.swipes:
                a = arts.get(s.article_id)
                if a is None or a["embedding"] is None:
                    continue
                rows.append((a["title"], "liked" if s.liked else "disliked", 0.7 if s.liked else -0.7,
                             a["embedding"], a["id"]))
                for t in a["topics"]:
                    if t in weights:
                        weights[t] = round(min(1.0, max(0.0, weights[t] + (0.1 if s.liked else -0.05))), 3)

        coords = await geocode(data.city)
        conn.execute(
            """update users set name=%s, city=%s, reading_minutes=%s, region_mix=%s, onboarded=true,
                   lat=coalesce(%s, lat), lon=coalesce(%s, lon) where id=%s""",
            (data.name, data.city, data.reading_minutes, data.region_mix,
             coords[0] if coords else None, coords[1] if coords else None, user["id"]))
        conn.execute(
            """insert into profiles (user_id, topics, entities, about) values (%s,%s,%s,%s)
               on conflict (user_id) do update set topics=excluded.topics, entities=excluded.entities,
                   about=excluded.about, updated_at=now()""",
            (user["id"], _json(weights), _json(entities), data.about))
        conn.execute("delete from interest_anchors where user_id = %s", (user["id"],))
        add_anchors(conn, user["id"], rows)
        conn.execute(
            "insert into profile_snapshots (user_id, topics, changes) values (%s,%s,%s)",
            (user["id"], _json(weights), _json([{"why": "Created from onboarding", "topics": topics}])))
    return get_profile(user["id"])


def get_profile(user_id) -> dict:
    with db() as conn:
        user = conn.execute(
            "select id, name, email, city, reading_minutes, region_mix, onboarded, is_demo from users where id=%s",
            (user_id,)).fetchone()
        prof = conn.execute("select topics, entities, about, source_affinity, updated_at from profiles "
                            "where user_id=%s", (user_id,)).fetchone()
        anchors = conn.execute(
            "select id, label, kind, round(weight::numeric, 2)::float as weight, created_at "
            "from interest_anchors where user_id=%s order by weight desc", (user_id,)).fetchall()
        snaps = conn.execute(
            "select taken_at, topics, changes from profile_snapshots where user_id=%s "
            "order by taken_at desc limit 14", (user_id,)).fetchall()
    return {"user": user, "profile": prof, "anchors": anchors, "snapshots": snaps}


def onboarding_headlines(limit: int = 12) -> list[dict]:
    """A diverse set of today's real headlines (one or two per topic, with images) to swipe on."""
    with db() as conn:
        rows = conn.execute(
            """select distinct on (topics[1]) id, title, source, image_url, topics
               from articles
               where embedding is not null and image_url is not null and cardinality(topics) > 0
                 and fetched_at > now() - interval '2 days' and source in (
                   'Dawn','Express Tribune','Geo News','BBC News','The Guardian','TechCrunch','The Verge',
                   'ESPNcricinfo','BBC Sport','Ars Technica','Business Recorder','The News')
               order by topics[1], published_at desc""").fetchall()
    return rows[:limit]


def _json(v):
    from psycopg.types.json import Jsonb

    return Jsonb(v)
