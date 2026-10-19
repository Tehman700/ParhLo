"""Grounded, verified summaries — produced once per article (shared by all readers), only when selected.

1. fetch full text (trafilatura); fall back to the RSS excerpt
2. summarize ONLY from that text (fast model, JSON)
3. verify: Jev (System One, ~0.4 s, calibrated) checks every claim against the source → summary_verified;
   the fast LLM is the fallback when Jev is unavailable
Answers the BBC/EBU finding that ~half of AI news answers contain significant errors.
"""

import asyncio
import json
import logging
import time

import httpx
import trafilatura
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.database import db
from app.parhlo import jev
from app.parhlo.ingest import UA
from app.services.llm import get_llm

log = logging.getLogger("parhlo.summarize")
MIN_FULLTEXT = 600


class Summary(BaseModel):
    summary: str = Field(description="2-3 sentence neutral summary using only facts in the source")
    points: list[str] = Field(description="2-3 key facts, each under 20 words, copied in meaning from the source")


class Verdict(BaseModel):
    supported: bool = Field(description="true only if every claim in the summary is stated in the source")
    unsupported_claims: list[str] = []


async def fetch_fulltext(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        r = await client.get(url)
        if r.status_code != 200:
            return None
        text = await asyncio.to_thread(trafilatura.extract, r.text, include_comments=False, include_tables=False)
        return text if text and len(text) >= MIN_FULLTEXT else None
    except Exception:
        return None


async def summarize_one(client: httpx.AsyncClient, art: dict, sem: asyncio.Semaphore) -> dict:
    async with sem:
        content = art.get("content") or await fetch_fulltext(client, art["url"])
        source_text = (content or f"{art['title']}. {art.get('rss_summary') or ''}")[:9000]
        grounded_in = "full article" if content else "headline and excerpt"
        llm, fast = get_llm(), get_settings().llm_fast_model
        try:
            style = ("Write 2-3 plain sentences." if content else
                     "The source is only a headline and a short excerpt: write ONE plain sentence saying what happened. "
                     "Do not repeat the headline word for word, never write 'the article discusses', "
                     "and return at most 1 key point.")
            s: Summary = await llm.json([{"role": "user", "content": (
                "Summarize this news article for a busy reader in plain English. Use ONLY facts stated in the source. "
                f"No speculation, no outside knowledge, no opinions. {style}\n\n"
                f"TITLE: {art['title']}\nSOURCE TEXT:\n{source_text}")}], schema=Summary, model=fast, reasoning_effort="minimal")
            points = s.points if content else s.points[:1]  # excerpt-only: don't pad with near-duplicate points
            check = await verify(source_text, s.summary, points)
            verified = check["supported"]
        except Exception as e:
            log.warning("summary failed for %s: %s", art["id"], e)
            s, points, verified, check = Summary(summary=art.get("rss_summary") or art["title"], points=[]), [], None, None
        return {"id": art["id"], "content": content, "summary": s.summary, "points": points,
                "verified": verified, "grounded_in": grounded_in, "check": check}


async def verify(source_text: str, summary: str, points: list[str]) -> dict:
    """Is every claim in the summary stated in the source? Jev first (fast, calibrated); LLM as fallback."""
    t = time.perf_counter()
    jv = await jev.check_summary(source_text, summary, points)
    if jv is not None:
        return {"by": "jev", "supported": jv.supported, "confidence": jv.confidence,
                "unsupported_probability": jv.unsupported_probability, "ms": round((time.perf_counter() - t) * 1000)}
    t = time.perf_counter()
    v: Verdict = await get_llm().json([{"role": "user", "content": (
        "Fact-check the SUMMARY against the SOURCE. A claim is supported only if the source states it. "
        f"\n\nSOURCE:\n{source_text}\n\nSUMMARY:\n{summary}\n" + "\n".join(f"- {p}" for p in points))}],
        schema=Verdict, model=get_settings().llm_fast_model, reasoning_effort="minimal")
    return {"by": "llm", "supported": v.supported, "confidence": None, "ms": round((time.perf_counter() - t) * 1000)}


def cached_summaries(article_ids: list[int]) -> dict[int, dict]:
    """Summaries already written (no AI calls) — the fast reprint uses these and excerpts for the rest."""
    with db() as conn:
        rows = conn.execute("select id, ai_summary, ai_points, summary_verified from articles "
                            "where id = any(%s) and ai_summary is not null", (article_ids,)).fetchall()
    return {r["id"]: _summary_out(r) for r in rows}


def _summary_out(r: dict) -> dict:
    meta = r["ai_points"] if isinstance(r["ai_points"], dict) else json.loads(r["ai_points"] or "{}")
    return {"summary": r["ai_summary"], "points": meta.get("points", []), "grounded_in": meta.get("grounded_in"),
            "verified": r["summary_verified"], "check": meta.get("check")}


# ── INGEST STEP 12 (detail) ── Summarize only the articles that don't have a summary yet (8 at a time),
# save the results ON THE ARTICLE so every reader reuses them, then return all summaries by id.
async def ensure_summaries(article_ids: list[int]) -> dict[int, dict]:
    """Summarize any of these articles that don't have a summary yet; return all summaries by id."""
    with db() as conn:
        rows = conn.execute(
            "select id, url, title, rss_summary, content, ai_summary, ai_points, summary_verified "
            "from articles where id = any(%s)", (article_ids,)).fetchall()
    todo = [r for r in rows if not r["ai_summary"]]
    if todo:
        sem = asyncio.Semaphore(8)
        async with httpx.AsyncClient(timeout=12, follow_redirects=True, headers={"User-Agent": UA}) as client:
            done = await asyncio.gather(*(summarize_one(client, r, sem) for r in todo))
        with db() as conn:
            for d in done:
                conn.execute(
                    """update articles set content = coalesce(%s, content), ai_summary = %s, ai_points = %s,
                       summary_verified = %s, summarized_at = now() where id = %s""",
                    (d["content"], d["summary"], Jsonb({"points": d["points"], "grounded_in": d["grounded_in"], "check": d["check"]}),
                     d["verified"], d["id"]))
        with db() as conn:
            rows = conn.execute(
                "select id, ai_summary, ai_points, summary_verified from articles where id = any(%s)",
                (article_ids,)).fetchall()
    return {r["id"]: _summary_out(r) for r in rows if r["ai_summary"]}


# ── INGEST STEP 12 ── The "story bank": write AI summaries for the day's ~120 most important stories AHEAD of time.
# Summaries are the slow, costly part of a paper (fetch the full article + AI + Jev check ≈ several seconds each).
# Doing them once at night, saved on the article, means:
#   • every reader shares them (one summary per article, not one per reader → much cheaper), and
#   • a reader's paper — and an instant reprint when they change interests — rarely waits for a summary.
async def prewarm(limit: int = 120, hours: int = 30) -> dict:
    """Story bank: summarize the day's most important unsummarized stories ahead of time (shared by every reader),
    so reprints and first papers rarely wait for a summary."""
    with db() as conn:
        # Pick: not yet summarized, has a vector, not junk, from the last 30 hours —
        # most important first (Jev importance from STEP 7), newest first among equals.
        ids = [r["id"] for r in conn.execute(
            """select id from articles where ai_summary is null and embedding is not null and coalesce(junk, 0) < 0.78
                 and published_at > now() - make_interval(hours => %s)
               order by coalesce(importance, 0.4) desc, published_at desc limit %s""", (hours, limit)).fetchall()]
    if ids:
        # For each: fetch the full article → gpt-5-nano summary from that text only → Jev checks it → save on the
        # article (ai_summary, ai_points, content). See ensure_summaries() / summarize_one() / verify() above.
        await ensure_summaries(ids)
    return {"prewarmed": len(ids)}
