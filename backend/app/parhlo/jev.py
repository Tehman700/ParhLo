"""Jev (TypeSafe "System One" model): fast, typed decisions with calibrated confidence.

ParhLo uses Jev to DECIDE and the LLM to WRITE:
  classify_article  → topic (Choice), junk (Noul), importance (Score) — one call per article
  check_summary     → does the summary contain claims not in the source? (Noul)

Every function returns None when Jev is disabled, slow or failing, so callers fall back to the
previous method (embedding tags, blocklist, LLM verification) and the paper is never blocked.
"""

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.parhlo.topics import TOPICS

log = logging.getLogger("parhlo.jev")
URL = "https://api.typesafe.ai/v1/systemone"
TIMEOUT = 12.0
RETRIES = 2

IMPORTANCE_LEVELS = [
    "Trivial: entertainment filler, quizzes, gossip",
    "Minor: niche or very local",
    "Notable: worth knowing for interested readers",
    "Important: affects many people in Pakistan or the region",
    "Major: top national or world news of the day",
]
SUPPORTED_BELOW = 0.3  # unsupported-claim probability under which a summary earns the ✓
JUNK_QUESTION = ("Is this NOT a real news report — e.g. a quiz, podcast or video listing, tag or round-up page, "
                 "advertisement, press release, crypto/exchange promotion, or clickbait?")


@dataclass
class ArticleDecision:
    topic: str
    topic_confidence: float
    second_topic: str | None
    junk: float          # 0..1
    importance: float    # 0..1


@dataclass
class SummaryCheck:
    supported: bool
    unsupported_probability: float  # 0..1
    confidence: float               # how sure we are of the verdict, 0..1


def enabled() -> bool:
    s = get_settings()
    return s.jev_enabled and bool(s.typesafe_api_key)


async def ask(state, questions: dict, client: httpx.AsyncClient | None = None) -> dict | None:
    """One System One call. Returns the answers map, or None on any failure (caller falls back)."""
    if not enabled():
        return None
    s = get_settings()
    body = {"model": s.jev_model, "state": state, "questions": questions}
    headers = {"Authorization": f"Bearer {s.typesafe_api_key}"}
    own = client is None
    client = client or httpx.AsyncClient(timeout=TIMEOUT)
    try:
        for attempt in range(RETRIES + 1):
            try:
                r = await client.post(URL, json=body, headers=headers)
                if r.status_code in (429, 529) and attempt < RETRIES:
                    await asyncio.sleep(0.6 * (attempt + 1))
                    continue
                if r.status_code != 200:
                    log.warning("jev HTTP %s: %s", r.status_code, r.text[:200])
                    return None
                return r.json().get("answers")
            except httpx.HTTPError as e:
                if attempt == RETRIES:
                    log.warning("jev unreachable: %s", e)
                    return None
        return None
    finally:
        if own:
            await client.aclose()


def _article_state(title: str, excerpt: str | None, source: str) -> dict:
    return {"source": source, "headline": title, "excerpt": (excerpt or "")[:600]}


# ── INGEST STEP 7 (detail) ── Ask Jev three typed questions about ONE article in a SINGLE API call.
# Jev (TypeSafe "System One") is a fast decision model: instead of free text it returns structured answers with
# probabilities and confidence. Each question has a type:
#   "choice" → pick one option from a list   (topic: which of our 17 topics, described in topics.py)
#   "noul"   → a yes/no probability 0..1     (junk: is this NOT real news?)
#   "score"  → a level on a scale            (importance: one of the 5 IMPORTANCE_LEVELS above)
# Returns an ArticleDecision, or None if Jev failed (the caller then keeps the embedding-based fallback tags).
async def classify_article(title: str, excerpt: str | None, source: str,
                           client: httpx.AsyncClient | None = None) -> ArticleDecision | None:
    # The "state" Jev reads: outlet, headline, and the first 600 characters of the excerpt.
    answers = await ask(_article_state(title, excerpt, source), {
        "topic": {"type": "choice", "instructions": "Which topic best fits this news story?",
                  "criteria": {slug: t["desc"] for slug, t in TOPICS.items()}},
        "junk": {"type": "noul", "instructions": JUNK_QUESTION},
        "importance": {"type": "score", "instructions": "How important is this story for a general news reader in Pakistan today?",
                       "criteria": IMPORTANCE_LEVELS},
    }, client)
    if not answers:
        return None
    try:
        topic = answers["topic"]
        # Jev returns a probability for EVERY topic. Sort them; keep the runner-up as a second topic only if it is
        # strong (≥ 0.25), e.g. a story that is both "economy" and "business".
        probs = sorted(topic["probabilities"].items(), key=lambda kv: -kv[1])
        second = probs[1][0] if len(probs) > 1 and probs[1][1] >= 0.25 else None
        # Package the answers. importance is scaled to 0..1 (level 0–4 ÷ 4), so ranking can use it directly;
        # junk ≥ 0.78 means the story is hidden from every paper (JUNK_THRESHOLD in ingest.py / rank.py).
        return ArticleDecision(
            topic=topic["choice"], topic_confidence=float(topic["confidence"]), second_topic=second,
            junk=float(answers["junk"]["noul"]),
            importance=round(float(answers["importance"]["score"]) / (len(IMPORTANCE_LEVELS) - 1), 3),
        )
    except (KeyError, TypeError, ValueError) as e:
        log.warning("jev classify parse failed: %s", e)
        return None


# ── INGEST STEP 7 (parallel) ── Classify MANY articles at once, but at most 12 at the same time.
# A semaphore is like 12 tickets: each request takes one and gives it back when done, so we stay fast
# (~0.4 s per call, 12 in flight) without flooding Jev's API with hundreds of simultaneous requests.
async def classify_many(items: list[dict], concurrency: int = 12) -> list[ArticleDecision | None]:
    """items: [{title, excerpt, source}] → decisions in the same order (None where Jev failed)."""
    if not enabled() or not items:
        return [None] * len(items)    # Jev off or nothing to do → every article uses the fallback tags
    sem = asyncio.Semaphore(concurrency)
    start = time.perf_counter()
    # One shared HTTP client for all calls (reuses connections).
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async def one(it):
            async with sem:           # wait for one of the 12 "tickets"
                return await classify_article(it["title"], it.get("excerpt"), it["source"], client)
        out = await asyncio.gather(*(one(i) for i in items))
    log.info("jev classified %d/%d articles in %.1fs", sum(o is not None for o in out), len(items), time.perf_counter() - start)
    return out


async def check_summary(source_text: str, summary: str, points: list[str]) -> SummaryCheck | None:
    """Jev's citation-check pattern: is anything in the summary NOT stated in the source?"""
    claim = summary + ("\n" + "\n".join(f"- {p}" for p in points) if points else "")
    answers = await ask(source_text[:12000], {
        "unsupported": {"type": "noul", "instructions": {
            "summary": claim,
            "question": "Does `summary` contain any claim, number, name or date that is NOT stated in the state (the source article)?",
        }},
    })
    if not answers:
        return None
    try:
        p = float(answers["unsupported"]["noul"])
    except (KeyError, TypeError, ValueError):
        return None
    # ✓ only when Jev is clearly sure there is nothing unsupported (p < 0.3 → ≥40% confidence).
    return SummaryCheck(supported=p < SUPPORTED_BELOW, unsupported_probability=round(p, 3),
                        confidence=round(abs(p - 0.5) * 2, 3))
