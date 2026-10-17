"""Grounded, verified summaries — produced once per article (shared by all readers), only when selected.

1. fetch full text (trafilatura); fall back to the RSS excerpt
2. summarize ONLY from that text (fast model, JSON)
3. verify: a second pass checks every summary claim against the source → summary_verified
Answers the BBC/EBU finding that ~half of AI news answers contain significant errors.
"""

import asyncio
import json
import logging

import httpx
import trafilatura
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.database import db
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
            s: Summary = await llm.json([{"role": "user", "content": (
                "Summarize this news article for a busy reader. Use ONLY facts stated in the source. "
                "No speculation, no outside knowledge, no opinions.\n\n"
                f"TITLE: {art['title']}\nSOURCE TEXT:\n{source_text}")}], schema=Summary, model=fast)
            v: Verdict = await llm.json([{"role": "user", "content": (
                "Fact-check the SUMMARY against the SOURCE. A claim is supported only if the source states it. "
                f"\n\nSOURCE:\n{source_text}\n\nSUMMARY:\n{s.summary}\n" + "\n".join(f"- {p}" for p in s.points))}],
                schema=Verdict, model=fast)
            verified = v.supported
        except Exception as e:
            log.warning("summary failed for %s: %s", art["id"], e)
            s, verified = Summary(summary=art.get("rss_summary") or art["title"], points=[]), None
        return {"id": art["id"], "content": content, "summary": s.summary, "points": s.points,
                "verified": verified, "grounded_in": grounded_in}


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
                    (d["content"], d["summary"], Jsonb({"points": d["points"], "grounded_in": d["grounded_in"]}),
                     d["verified"], d["id"]))
        with db() as conn:
            rows = conn.execute(
                "select id, ai_summary, ai_points, summary_verified from articles where id = any(%s)",
                (article_ids,)).fetchall()
    out = {}
    for r in rows:
        meta = r["ai_points"] if isinstance(r["ai_points"], dict) else json.loads(r["ai_points"] or "{}")
        out[r["id"]] = {"summary": r["ai_summary"], "points": meta.get("points", []),
                        "grounded_in": meta.get("grounded_in"), "verified": r["summary_verified"]}
    return out
