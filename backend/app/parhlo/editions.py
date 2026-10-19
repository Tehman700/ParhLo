"""④ PUBLISH — generate and freeze a reader's daily edition (web and PDF both render this JSON)."""

import asyncio
import logging
import time
from datetime import date, datetime, timedelta, timezone

from psycopg.types.json import Jsonb

from app.core.database import db
from app.core.errors import AppError, NotFoundError
from app.parhlo import friends
from app.parhlo.editor import edit_paper, fallback_layout
from app.parhlo.ingest import ingest
from app.parhlo.morning import morning_box
from app.parhlo.rank import rank_for_user, select_stories, story_count
from app.parhlo.summarize import cached_summaries, ensure_summaries
from app.parhlo.topics import TOPICS

log = logging.getLogger("parhlo.editions")
PKT = timezone(timedelta(hours=5))


def today_pkt() -> date:
    return datetime.now(PKT).date()


JOB_STALE_MIN = 3


async def generate_edition(user: dict, edition_date: date | None = None, force: bool = False, fast: bool = False) -> dict:
    """fast=True: a reprint with no AI calls in the critical path (stored summaries or excerpts, simple layout,
    morning box from the cache); polish_edition() then upgrades it in the background."""
    """Build (or return) a reader's paper. Only one build runs per reader and date: a second request
    (e.g. the dashboard and the paper page at once) waits for the first one's result."""
    edition_date = edition_date or today_pkt()
    started = datetime.now(timezone.utc)
    with db() as conn:
        existing = conn.execute("select * from editions where user_id=%s and edition_date=%s",
                                (user["id"], edition_date)).fetchone()
        if existing and not force:
            return _public(existing)
        claimed = conn.execute(
            """insert into edition_jobs (user_id, edition_date) values (%s,%s)
               on conflict (user_id, edition_date) do update set started_at = now()
                 where edition_jobs.started_at < now() - make_interval(mins => %s)
               returning started_at""", (user["id"], edition_date, JOB_STALE_MIN)).fetchone()
    if not claimed:
        return await _wait_for_edition(user["id"], edition_date, started if force else None)
    try:
        return await _build(user, edition_date, fast)
    finally:
        with db() as conn:
            conn.execute("delete from edition_jobs where user_id=%s and edition_date=%s", (user["id"], edition_date))


async def _wait_for_edition(user_id, edition_date: date, newer_than: datetime | None) -> dict:
    for _ in range(80):
        await asyncio.sleep(1.5)
        with db() as conn:  # job first, then the row: a build that just finished is always seen
            busy = conn.execute("select 1 from edition_jobs where user_id=%s and edition_date=%s",
                                (user_id, edition_date)).fetchone()
            row = conn.execute("select * from editions where user_id=%s and edition_date=%s",
                               (user_id, edition_date)).fetchone()
        if row and (newer_than is None or row["created_at"] >= newer_than):
            return _public(row)
        if not busy:
            break
    raise AppError("Your paper is taking longer than usual. Please try again in a moment.", 503)


async def _build(user: dict, edition_date: date, fast: bool = False) -> dict:
    t0 = time.perf_counter()
    timings: dict[str, int] = {}

    def lap(name: str) -> None:
        timings[name] = round((time.perf_counter() - t0) * 1000) - sum(timings.values())

    with db() as conn:
        current = conn.execute("select data from editions where user_id=%s and edition_date=%s",
                               (user["id"], edition_date)).fetchone()
        fresh = 999 if fast else conn.execute("select count(*) as n from articles where embedding is not null "
                                              "and fetched_at > now() - interval '3 hours'").fetchone()["n"]
        prof = conn.execute("select topics, entities from profiles where user_id=%s", (user["id"],)).fetchone()
        prior = conn.execute(
            "select data from editions where user_id=%s and edition_date < %s order by edition_date desc limit 1",
            (user["id"], edition_date)).fetchone()
        prior_ids = {s["id"] for s in (prior["data"]["stories"] if prior else [])}
        number = conn.execute("select count(*) as n from editions where user_id=%s and edition_date < %s",
                              (user["id"], edition_date)).fetchone()["n"] + 1

    if fresh < 40 and not fast:  # keep the pool fresh; also searches Google News for the reader's own interests
        entities = (prof or {}).get("entities") or []
        await ingest(extra_queries=entities[:6])

    prior_titles = [t for s in (prior["data"]["stories"] if prior else []) for t in (s.get("title"), s.get("headline"))]
    lap("prepare")
    pool = rank_for_user(user, exclude_ids=prior_ids, avoid_titles=prior_titles)
    if not pool:
        raise NotFoundError("No articles available yet — try again in a minute.")
    on_topics = [t for t, w in sorted(((prof or {}).get("topics") or {}).items(), key=lambda kv: -kv[1]) if w >= 0.5]
    picks = select_stories(pool, story_count(user["reading_minutes"]), on_topics=on_topics)
    picks = friends.add_friend_picks(user, pool, picks)
    lap("rank")
    ids = [p["id"] for p in picks]
    summaries = cached_summaries(ids) if fast else await ensure_summaries(ids)
    stories = [{**p, **summaries.get(p["id"], _excerpt(p))} for p in picks]
    lap("summaries")

    topics = (prof or {}).get("topics") or {}
    top_topics = [TOPICS[t]["label"] for t, _ in sorted(topics.items(), key=lambda kv: -kv[1])[:5] if t in TOPICS]
    same_city = current and current["data"].get("reader", {}).get("city") == user["city"]
    morning = current["data"]["morning"] if fast and same_city and current["data"].get("morning", {}).get("weather") \
        else await morning_box(user["city"], user["lat"], user["lon"])
    lap("morning")
    if fast:
        layout = fallback_layout(user, stories)
        layout["editor_note"] = _quick_note(stories, top_topics)
        layout["quiz"] = (current["data"].get("quiz") if current else None) or []
    else:
        layout = await edit_paper(user, stories, top_topics, morning)
    lap("editor")
    # The front page is one of THEIR stories (Top stories are shared by everyone and keep their badge further down).
    layout["lead_id"] = _pick_lead(stories)
    _apply_why(layout, stories)

    data = {
        "date": edition_date.isoformat(),
        "number": number,
        "reader": {"name": user["name"], "city": user["city"]},
        "editor_note": layout["editor_note"],
        "morning": morning,
        "lead_id": layout["lead_id"],
        "sections": layout["sections"],
        "three_things": layout["three_things"],
        "quiz": layout["quiz"],                                       # shown in tomorrow's paper
        "recall_quiz": (prior["data"].get("quiz") if prior else []) or [],  # yesterday's 3 things
        "stories": [_story_out(s, layout["edits"].get(s["id"], {})) for s in stories],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": "fast" if fast else "full",          # fast → polish_edition() upgrades it in the background
        "build_ms": timings,
    }
    with db() as conn:
        row = conn.execute(
            """insert into editions (user_id, edition_date, number, data) values (%s,%s,%s,%s)
               on conflict (user_id, edition_date) do update set data = excluded.data, pdf_key = null,
                   audio_key = null, created_at = now()
               returning *""", (user["id"], edition_date, number, Jsonb(data))).fetchone()
        lead = next((st["headline"] for st in data["stories"] if st["id"] == data["lead_id"]), None)
        if not user.get("is_demo") and not current:  # first print of the day only, not reprints
            friends.notify(conn, user["id"], "paper_ready", data={"date": data["date"], "lead": lead})
    return _public(row)


def _excerpt(p: dict) -> dict:
    return {"summary": p["rss_summary"] or p["title"], "points": [], "verified": None, "grounded_in": "excerpt", "check": None}


def _quick_note(stories: list[dict], top_topics: list[str]) -> str:
    personal = [s for s in stories if not s.get("core") and not s.get("discovery")]
    interests = ", ".join(top_topics[:3]) or "your interests"
    return f"Updated for {interests}: {len(personal)} stories picked for you, plus today's biggest news."


def _apply_why(layout: dict, stories: list[dict]) -> None:
    for s in stories:  # reasons that come from how a story was picked are stated by us, not the editor
        why = layout["edits"].setdefault(s["id"], {})
        if s.get("friend"):
            why["why"] = f"{s['friend']} {'saved' if s.get('friend_saved') else 'liked'} this"
        elif s.get("core"):
            why["why"] = "One of today's biggest stories"
        elif s.get("discovery"):
            why["why"] = f"Something new for you: {TOPICS[s['topics'][0]]['label'] if s.get('topics') and s['topics'][0] in TOPICS else 'outside your usual topics'}"
        elif s.get("match"):   # ranking knows the exact interest: state it (the editor's why-line only guesses)
            why["why"] = f"Because you follow {s['match']}"
        elif not why.get("why"):
            topic = TOPICS.get((s.get("topics") or [""])[0], {}).get("label")
            why["why"] = (f"Because you follow {s['match']}" if s.get("match")
                          else f"Because you read and like {topic} stories" if topic else "Picked from what you read")


def _pick_lead(stories: list[dict]) -> int:
    """The reader's strongest personal story (by ranking score, so a topic they just switched on leads),
    preferring one of the top three we could read in full."""
    personal = sorted((s for s in stories if not s.get("core") and not s.get("discovery")),
                      key=lambda s: -s.get("score", 0)) or stories
    return next((s for s in personal[:3] if s.get("grounded_in") == "full article"), personal[0])["id"]


async def polish_edition(user: dict, edition_date: date) -> dict | None:
    """Upgrade a fast reprint in place: AI summaries for stories that only had excerpts, then the AI editor
    (headlines, why-lines, sections, editor's note, 3 things, quiz). Same stories, same order of importance."""
    with db() as conn:  # claim it, so the page and n8n never polish the same paper twice
        row = conn.execute(
            """update editions set data = jsonb_set(data, '{phase}', '"polishing"')
               where user_id=%s and edition_date=%s and data->>'phase' = 'fast' returning *""",
            (user["id"], edition_date)).fetchone()
    if not row:
        return None
    version = row["data"]["generated_at"]  # if a newer reprint lands meanwhile, this polish is discarded
    try:
        t0 = time.perf_counter()
        data = row["data"]
        ids = [s["id"] for s in data["stories"]]
        summaries = await ensure_summaries(ids)
        with db() as conn:
            arts = {a["id"]: a for a in conn.execute(
                "select id, title, source, source_region, topics, published_at, image_url, url, rss_summary, importance, "
                "language, link "
                "from articles where id = any(%s)", (ids,)).fetchall()}
            prof = conn.execute("select topics from profiles where user_id=%s", (user["id"],)).fetchone()
        stories = []
        for s in data["stories"]:
            a = arts.get(s["id"])
            if not a:
                continue
            stories.append({**a, **summaries.get(s["id"], _excerpt(a)), "core": s.get("core"), "discovery": s.get("discovery"),
                            "friend": s.get("friend"), "also_sources": s.get("also_reported_by"),
                            "score": len(ids) - ids.index(s["id"]), "match": None, "why_before": s.get("why")})
        topics = (prof or {}).get("topics") or {}
        top_topics = [TOPICS[t]["label"] for t, _ in sorted(topics.items(), key=lambda kv: -kv[1])[:5] if t in TOPICS]
        layout = await edit_paper(user, stories, top_topics, data["morning"])
        _apply_why(layout, stories)
        for s in stories:  # keep the personal reason from the fast print if the editor gave none — and always when
            # ranking knew the exact interest ("Because you follow Cat News"): that's a fact, the editor only guesses
            known = (s["why_before"] or "").startswith("Because you follow ") and not (
                s.get("core") or s.get("discovery") or s.get("friend"))
            if known or not layout["edits"][s["id"]].get("why"):
                layout["edits"][s["id"]]["why"] = s["why_before"]
        data.update({
            "editor_note": layout["editor_note"], "sections": layout["sections"], "three_things": layout["three_things"],
            "quiz": layout["quiz"] or data.get("quiz") or [],
            "lead_id": data["lead_id"] if data["lead_id"] in {s["id"] for s in stories} else _pick_lead(stories),
            "stories": [_story_out(s, layout["edits"].get(s["id"], {})) for s in stories],
            "generated_at": datetime.now(timezone.utc).isoformat(), "phase": "full",
            "build_ms": {**data.get("build_ms", {}), "polish": round((time.perf_counter() - t0) * 1000)},
        })
        with db() as conn:
            row = conn.execute("update editions set data = %s, pdf_key = null where id = %s "   # stored PDF is stale now
                               "and data->>'generated_at' = %s returning *",
                               (Jsonb(data), row["id"], version)).fetchone()
        return _public(row) if row else None
    except Exception:
        with db() as conn:  # release the claim so it can be retried
            conn.execute("update editions set data = jsonb_set(data, '{phase}', '\"fast\"') where id = %s "
                         "and data->>'generated_at' = %s", (row["id"], version))
        raise


def _story_out(s: dict, edit: dict) -> dict:
    return {
        "id": s["id"], "headline": edit.get("headline") or s["title"], "title": s["title"],
        "source": s["source"], "url": s.get("link") or s["url"], "image": s["image_url"],
        "published_at": s["published_at"].isoformat() if s.get("published_at") else None,
        "topics": s["topics"], "summary": s["summary"], "points": s.get("points") or [],
        "verified": s.get("verified"), "grounded_in": s.get("grounded_in"),
        "why": edit.get("why") or (f"Matches your interest in {s['match']}" if s.get("match") else None),
        "discovery": bool(s.get("discovery")), "core": bool(s.get("core")), "friend": s.get("friend"),
        "importance": s.get("importance"), "check": s.get("check"),
        "also_reported_by": [x for x in (s.get("also_sources") or []) if x][:5],
        "region": s["source_region"],
        "language": s.get("language") or "en",   # SWS: non-English sources show "Translated from …"
    }


def _public(row: dict) -> dict:
    return {"id": row["id"], "edition_date": row["edition_date"].isoformat(), "number": row["number"],
            "pdf_key": row.get("pdf_key"), "audio_key": row.get("audio_key"), **row["data"]}


def list_editions(user_id) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """select id, edition_date, number, data->>'editor_note' as editor_note,
                      jsonb_array_length(data->'stories') as stories,
                      (select s->>'headline' from jsonb_array_elements(data->'stories') s
                        where (s->>'id')::bigint = (data->>'lead_id')::bigint) as lead_headline
               from editions where user_id=%s order by edition_date desc""", (user_id,)).fetchall()
    return [{**r, "edition_date": r["edition_date"].isoformat()} for r in rows]


def get_edition(user_id, edition_date: date) -> dict:
    with db() as conn:
        row = conn.execute("select * from editions where user_id=%s and edition_date=%s",
                           (user_id, edition_date)).fetchone()
    if not row:
        raise NotFoundError(f"No edition for {edition_date}")
    return _public(row)
