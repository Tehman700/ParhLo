"""English headlines for kept non-English stories (GDELT translated files, native Google News editions).

Runs after the gate, so only stories some reader could get are translated: one gpt-5-nano call per 40 headlines.
Summaries need nothing extra — summarize.py writes them in English from the original article text.
If the call fails, the original headline stays (the story still works; the AI editor rewrites headlines later).
"""

import logging

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.parhlo.sws.languages import name
from app.services.llm import get_llm

log = logging.getLogger("parhlo.sws.translate")
BATCH = 40


class Titles(BaseModel):
    titles: list[str] = Field(description="the English headlines, same order and count as given")


async def english_titles(items: list[dict]) -> int:
    """Translate the headlines of non-English items in place. Returns how many were translated."""
    todo = [i for i in items if i.get("language") not in (None, "en")]
    done = 0
    for start in range(0, len(todo), BATCH):
        batch = todo[start:start + BATCH]
        listing = "\n".join(f"{n}. [{name(i['language']) or i['language']}] {i['title']}" for n, i in enumerate(batch, 1))
        try:
            out: Titles = await get_llm().json([{"role": "user", "content": (
                "Translate these news headlines into plain, natural English. Keep names, numbers and places exact; "
                "don't add anything. Return exactly one English headline per line given, in the same order.\n\n"
                + listing)}], schema=Titles, model=get_settings().llm_fast_model, reasoning_effort="minimal")
        except Exception as e:
            log.warning("headline translation failed: %s", e)
            continue
        if len(out.titles) != len(batch):
            log.warning("headline translation returned %d for %d", len(out.titles), len(batch))
            continue
        for item, title in zip(batch, out.titles):
            if title.strip():
                item["title"] = " ".join(title.split())[:300]
                done += 1
    return done
