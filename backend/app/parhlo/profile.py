"""Reader memory, layer 1 and 2: explicit profile (topic weights, entities) + interest anchors (embeddings)."""

import re

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


TRUSTED_SOURCES = ("Dawn", "Express Tribune", "Geo News", "The News", "Business Recorder", "BBC News", "BBC Sport",
                   "The Guardian", "The New York Times", "TechCrunch", "The Verge", "Ars Technica", "ESPNcricinfo")


def _candidates(require_image: bool) -> list[dict]:
    """Today's real, Jev-approved headlines from trusted outlets, most important first."""
    with db() as conn:
        return conn.execute(
            f"""select id, title, source, image_url, topics, coalesce(importance, 0.4) as importance,
                       coalesce(cluster_id, id) as story
                from articles
                where embedding is not null and cardinality(topics) > 0 and coalesce(junk, 0) < 0.78
                  and fetched_at > now() - interval '2 days' and source = any(%s)
                  {"and image_url is not null" if require_image else ""}
                order by importance desc nulls last, published_at desc limit 3000""",
            (list(TRUSTED_SOURCES),)).fetchall()


def _words(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", title.lower())}


def same_story(a: str, b: str) -> bool:
    """Headline overlap check for stories two outlets worded differently (Jaccard ≥ 0.3 on 4+ letter words)."""
    wa, wb = _words(a), _words(b)
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.3


def _real_headlines(rows: list[dict]) -> list[dict]:
    """Drop 1–3 word editorial titles ("No talks") and keep one article per story across outlets."""
    out, stories = [], set()
    for r in rows:
        if len(re.findall(r"[A-Za-z]{3,}", r["title"])) < 4 or r.get("story") in stories:
            continue
        if any(same_story(r["title"], o["title"]) for o in out[:60]):  # top stories are where duplicates hurt
            continue
        stories.add(r.get("story"))
        out.append(r)
    return out


def _pick(rows: list[dict], topics: list[str], per_topic: int, extra: int) -> list[dict]:
    """Up to `per_topic` stories per chosen topic (round-robin, so every topic shows up early),
    then `extra` important stories from other topics (one per topic) to discover hidden interests."""
    chosen, used_ids, seen_titles = [], set(), set()

    def take(row, topic, discovery):
        key = row["title"].lower()[:60]
        if row["id"] in used_ids or key in seen_titles:
            return False
        used_ids.add(row["id"])
        seen_titles.add(key)
        chosen.append({**row, "topic": topic, "discovery": discovery})
        return True

    by_topic: dict[str, list[dict]] = {}
    for r in rows:
        by_topic.setdefault(r["topics"][0], []).append(r)
    for round_ in range(per_topic):
        for t in topics:
            for r in by_topic.get(t, []):
                if take(r, t, False):
                    break
    others = [t for t in by_topic if t not in topics]
    others.sort(key=lambda t: -by_topic[t][0]["importance"])
    for t in others[:extra]:
        for r in by_topic[t]:
            if take(r, t, True):
                break
    return chosen


def onboarding_headlines(topics: list[str] | None = None, limit: int = 10) -> list[dict]:
    """Real headlines to swipe on. With topics: chosen topics first, then 3 discovery headlines."""
    topics = [t for t in (topics or []) if t in TOPICS]
    rows = _real_headlines(_candidates(require_image=True))
    if not topics:  # no picks yet: one per topic, most important first
        return _pick(rows, [], 0, limit)
    per_topic = max(1, min(3, (limit - 3) // len(topics)))
    return _pick(rows, topics, per_topic, 3)[:limit]


def onboarding_preview(topics: list[str], entities: list[str] | None = None) -> dict:
    """A mini front page for the topics picked so far: today's top stories + the reader's topics."""
    topics = [t for t in topics if t in TOPICS]
    rows = _real_headlines(_candidates(require_image=False))
    core = [{**r, "topic": r["topics"][0], "core": True} for r in rows[:2]]
    core_ids = {r["id"] for r in core}
    personal = _pick([r for r in rows if r["id"] not in core_ids], topics, 2, 0)[:6]
    if entities:  # followed names that appear in today's headlines
        names = [e.lower() for e in entities if e.strip()]
        hits = [r for r in rows if any(n in r["title"].lower() for n in names) and r["id"] not in core_ids]
        personal = [{**h, "topic": h["topics"][0], "followed": True} for h in hits[:2]] +                    [p for p in personal if p["id"] not in {h["id"] for h in hits[:2]}]
    lead = next((p for p in personal if p.get("image_url")), personal[0] if personal else None)
    return {"lead": lead, "stories": [p for p in personal if p is not lead][:5], "core": core}


def _json(v):
    from psycopg.types.json import Jsonb

    return Jsonb(v)
