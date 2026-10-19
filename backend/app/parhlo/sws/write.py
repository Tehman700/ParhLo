"""Richer summaries for stories fetched because a reader changed their interests (web search).

These stories come with the full article text (Tavily raw content or the publisher page), so the stronger model
(gpt-5-mini, the editor's model) writes a fuller summary — 4–6 sentences and 3–5 key points — straight from it.
No Jev step here (by design): the text is the source, the prompt forbids anything not in it, and the story
still links to the original. Stored on the article, so every paper and reader reuses it.
"""

import asyncio
import logging

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.llm import get_llm

log = logging.getLogger("parhlo.sws.write")
CONCURRENCY = 6
SOURCE_CHARS = 12000


class RichSummary(BaseModel):
    summary: str = Field(description="4-6 plain sentences: what happened, who is involved, why it matters, what's next "
                                     "— only facts stated in the source")
    points: list[str] = Field(description="3-5 key facts, each under 25 words, copied in meaning from the source")


async def _one(item: dict, sem: asyncio.Semaphore) -> bool:
    async with sem:
        try:
            out: RichSummary = await get_llm().json([{"role": "user", "content": (
                "Summarize this news article for a reader who wants to understand it properly, in plain English "
                "(write in English even if the source is in another language). Use ONLY facts stated in the source: "
                "no speculation, no outside knowledge, no opinions. Give the full picture: what happened, who is "
                "involved, why it matters and what happens next, where the source says so.\n\n"
                f"TITLE: {item['title']}\nSOURCE TEXT:\n{item['content'][:SOURCE_CHARS]}")}],
                schema=RichSummary, model=get_settings().llm_model, reasoning_effort="low")
        except Exception as e:
            log.warning("rich summary failed for %s: %s", item["url"], e)
            return False
    item["ai_summary"] = out.summary.strip()
    item["ai_points"] = {"points": [p.strip() for p in out.points if p.strip()][:5], "grounded_in": "full article",
                         "check": None, "by": "gpt-5-mini"}
    return True


async def write_rich(items: list[dict]) -> int:
    """Write rich summaries (in place) for items that have the full text. Returns how many were written."""
    todo = [i for i in items if i.get("content") and not i.get("ai_summary")]
    sem = asyncio.Semaphore(CONCURRENCY)
    return sum(await asyncio.gather(*(_one(i, sem) for i in todo)))
