"""④ PUBLISH — generate and freeze a reader's daily edition (web and PDF both render this JSON)."""

import logging
from datetime import date, datetime, timedelta, timezone

from psycopg.types.json import Jsonb

from app.core.database import db
from app.core.errors import NotFoundError
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


async def generate_edition(user: dict, edition_date: date | None = None, force: bool = False) -> dict:
    edition_date = edition_date or today_pkt()
    with db() as conn:
        existing = conn.execute("select * from editions where user_id=%s and edition_date=%s",
                                (user["id"], edition_date)).fetchone()
        if existing and not force:
            return _public(existing)
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

    pool = rank_for_user(user, exclude_ids=prior_ids)
    if not pool:
        raise NotFoundError("No articles available yet — try again in a minute.")
    picks = select_stories(pool, story_count(user["reading_minutes"]))
    summaries = await ensure_summaries([p["id"] for p in picks])
    stories = [{**p, **summaries.get(p["id"], {"summary": p["rss_summary"] or p["title"], "points": [],
                                               "verified": None, "grounded_in": "excerpt"})} for p in picks]

    topics = (prof or {}).get("topics") or {}
    top_topics = [TOPICS[t]["label"] for t, _ in sorted(topics.items(), key=lambda kv: -kv[1])[:5] if t in TOPICS]
    morning = await morning_box(user["city"], user["lat"], user["lon"])
    layout = await edit_paper(user, stories, top_topics, morning)

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
    return _public(row)


def _story_out(s: dict, edit: dict) -> dict:
    return {
        "id": s["id"], "headline": edit.get("headline") or s["title"], "title": s["title"],
        "source": s["source"], "url": s["url"], "image": s["image_url"],
        "published_at": s["published_at"].isoformat() if s.get("published_at") else None,
        "topics": s["topics"], "summary": s["summary"], "points": s.get("points") or [],
        "verified": s.get("verified"), "grounded_in": s.get("grounded_in"),
        "why": edit.get("why") or (f"Because you follow {s['match']}" if s.get("match") else None),
        "discovery": bool(s.get("discovery")), "also_reported_by": [x for x in (s.get("also_sources") or []) if x][:5],
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
