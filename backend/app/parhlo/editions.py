"""④ PUBLISH — generate and freeze a reader's daily edition (web and PDF both render this JSON)."""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from psycopg.types.json import Jsonb

from app.core.database import db
from app.core.errors import AppError, NotFoundError
from app.parhlo import friends
from app.parhlo.editor import edit_paper
from app.parhlo.ingest import ingest
from app.parhlo.morning import morning_box
from app.parhlo.rank import rank_for_user, select_stories, story_count
from app.parhlo.summarize import ensure_summaries
from app.parhlo.topics import TOPICS

log = logging.getLogger("parhlo.editions")
PKT = timezone(timedelta(hours=5))


def today_pkt() -> date:
    return datetime.now(PKT).date()


JOB_STALE_MIN = 3


async def generate_edition(user: dict, edition_date: date | None = None, force: bool = False) -> dict:
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
        return await _build(user, edition_date)
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


async def _build(user: dict, edition_date: date) -> dict:
    with db() as conn:
        fresh = conn.execute("select count(*) as n from articles where embedding is not null "
                             "and fetched_at > now() - interval '3 hours'").fetchone()["n"]
        prof = conn.execute("select topics, entities from profiles where user_id=%s", (user["id"],)).fetchone()
        prior = conn.execute(
            "select data from editions where user_id=%s and edition_date < %s order by edition_date desc limit 1",
            (user["id"], edition_date)).fetchone()
        prior_ids = {s["id"] for s in (prior["data"]["stories"] if prior else [])}
        number = conn.execute("select count(*) as n from editions where user_id=%s and edition_date < %s",
                              (user["id"], edition_date)).fetchone()["n"] + 1

    if fresh < 40:  # keep the pool fresh; also searches Google News for the reader's own interests
        entities = (prof or {}).get("entities") or []
        await ingest(extra_queries=entities[:6])

    prior_titles = [t for s in (prior["data"]["stories"] if prior else []) for t in (s.get("title"), s.get("headline"))]
    pool = rank_for_user(user, exclude_ids=prior_ids, avoid_titles=prior_titles)
    if not pool:
        raise NotFoundError("No articles available yet — try again in a minute.")
    picks = select_stories(pool, story_count(user["reading_minutes"]))
    picks = friends.add_friend_picks(user, pool, picks)
    summaries = await ensure_summaries([p["id"] for p in picks])
    stories = [{**p, **summaries.get(p["id"], {"summary": p["rss_summary"] or p["title"], "points": [],
                                               "verified": None, "grounded_in": "excerpt", "check": None})} for p in picks]

    topics = (prof or {}).get("topics") or {}
    top_topics = [TOPICS[t]["label"] for t, _ in sorted(topics.items(), key=lambda kv: -kv[1])[:5] if t in TOPICS]
    morning = await morning_box(user["city"], user["lat"], user["lon"])
    layout = await edit_paper(user, stories, top_topics, morning)
    # The lead is the reader's front page: one of THEIR stories (Top stories are shared by everyone and keep their
    # badge further down), and one we could read in full (better summary, real ✓).
    personal = [s for s in stories if not s.get("core") and not s.get("discovery")]
    chosen = next((s for s in personal if s["id"] == layout["lead_id"]), None)
    if not chosen or chosen.get("grounded_in") != "full article":
        full = [s for s in personal if s.get("grounded_in") == "full article"]
        pick = max(full or personal or stories, key=lambda s: s.get("score", 0))
        layout["lead_id"] = pick["id"]
    for s in stories:  # reasons that come from how a story was picked are stated by us, not the editor
        why = layout["edits"].setdefault(s["id"], {})
        if s.get("friend"):
            why["why"] = f"{s['friend']} {'saved' if s.get('friend_saved') else 'liked'} this"
        elif s.get("core"):
            why["why"] = "One of today's biggest stories"
        elif s.get("discovery"):
            why["why"] = f"Something new for you: {TOPICS[s['topics'][0]]['label'] if s.get('topics') and s['topics'][0] in TOPICS else 'outside your usual topics'}"

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
    }
    with db() as conn:
        row = conn.execute(
            """insert into editions (user_id, edition_date, number, data) values (%s,%s,%s,%s)
               on conflict (user_id, edition_date) do update set data = excluded.data, pdf_key = null,
                   audio_key = null, created_at = now()
               returning *""", (user["id"], edition_date, number, Jsonb(data))).fetchone()
        lead = next((st["headline"] for st in data["stories"] if st["id"] == data["lead_id"]), None)
        if not user.get("is_demo"):
            friends.notify(conn, user["id"], "paper_ready", data={"date": data["date"], "lead": lead})
    return _public(row)


def _story_out(s: dict, edit: dict) -> dict:
    return {
        "id": s["id"], "headline": edit.get("headline") or s["title"], "title": s["title"],
        "source": s["source"], "url": s["url"], "image": s["image_url"],
        "published_at": s["published_at"].isoformat() if s.get("published_at") else None,
        "topics": s["topics"], "summary": s["summary"], "points": s.get("points") or [],
        "verified": s.get("verified"), "grounded_in": s.get("grounded_in"),
        "why": edit.get("why") or (f"Matches your interest in {s['match']}" if s.get("match") else None),
        "discovery": bool(s.get("discovery")), "core": bool(s.get("core")), "friend": s.get("friend"),
        "importance": s.get("importance"), "check": s.get("check"),
        "also_reported_by": [x for x in (s.get("also_sources") or []) if x][:5],
        "region": s["source_region"],
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
