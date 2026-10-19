"""SWS quality gate: which worldwide stories are worth keeping — decided after embedding, before Jev.

Embedding a headline costs almost nothing; Jev and AI summaries cost real money. GDELT sees ~800 English articles
every 15 minutes, most of them small-town or lifestyle pieces no reader would get, plus press releases and
auto-generated stock pages. The gate keeps an item when:

  requested  a reader asked for it: on-demand web search, or news fetched for a name just followed → kept
  followed   it's about a country (or name) a reader follows, e.g. GDELT country "Uganda"   → kept
  trusted    it's from an outlet we trust (rank.CURATED / KNOWN_GOOD, incl. world outlets) → kept
  relevant   its headline matches at least one reader's memory (cosine ≥ the source's bar) → kept
and drops it when it's blocked (press-release wire, stock spam, "watch live" spam) or matches nobody.
Kept items are ordered by how strong the reason is and capped per run, so Jev spend stays predictable.

Calibrated on 2026-10-19 (400 GDELT headlines vs 91 reader memories): median best match 0.26 (curated RSS: 0.37);
a 0.40 bar keeps ~6% of GDELT — about 50 stories per 15-minute window — before the cap.
"""

from collections import Counter

import numpy as np

from app.core.database import db
from app.parhlo.rank import CURATED, KNOWN_GOOD, SPAM, as_np
from app.parhlo.sws.outlets import blocked

# Minimum best-match to a reader memory, by origin. Google News top stories are already editor-picked,
# so they need less; GDELT is everything on the web, so it needs more.
RELEVANCE_BAR = {"gdelt": 0.40, "gnews": 0.33, "rss": 0.0, "web": 0.0}
MAX_KEEP = 60   # per run: the strongest reasons first


def load_interests() -> tuple[np.ndarray, set[str]]:
    """Every reader's positive memories (unit vectors) and the names / countries they follow (lower-case).
    Few hundred rows today; loading them once per run is far faster than comparing inside SQL (9 s for 400)."""
    with db() as conn:
        rows = conn.execute("select embedding from interest_anchors where weight > 0").fetchall()
        ents = conn.execute("select entities from profiles").fetchall()
    anchors = np.vstack([as_np(r["embedding"]) for r in rows]) if rows else np.zeros((0, 1536), np.float32)
    followed = {e.strip().lower() for r in ents for e in (r["entities"] or []) if e and e.strip()}
    return anchors, followed


def decide(items: list[dict], vectors: np.ndarray, anchors: np.ndarray, followed: set[str],
           max_keep: int = MAX_KEEP) -> tuple[list[bool], dict]:
    """Pure decision (no I/O): one bool per item, plus counts of each reason."""
    best = (np.asarray(vectors, np.float32) @ anchors.T).max(axis=1) if len(anchors) else np.zeros(len(items))
    scored: list[tuple[float, int, str]] = []   # (strength, index, reason)
    reasons: Counter[str] = Counter()
    rejected: list[str] = []                     # blocked / irrelevant URLs: skipped by later runs for 3 days
    for k, item in enumerate(items):
        origin, sim = item.get("origin", "rss"), float(best[k])
        if blocked(item["source"], item["url"], item["title"]) or SPAM.search(item["title"]):
            reasons["blocked"] += 1
            rejected.append(item["url"])
        elif origin in ("web", "rss") or item.get("requested"):
            reason = "requested" if item.get("requested") else origin
            scored.append((3.0, k, reason))           # asked for, or curated (rss): never gated away
        elif (item.get("country") or "").lower() in followed:
            scored.append((2.0 + sim, k, "followed"))
        elif item["source"] in CURATED or item["source"] in KNOWN_GOOD:
            scored.append((1.0 + sim, k, "trusted"))
        elif sim >= RELEVANCE_BAR.get(origin, 0.40):
            scored.append((sim, k, "relevant"))
        else:
            reasons["irrelevant"] += 1
            rejected.append(item["url"])
    scored.sort(reverse=True)
    keep = [False] * len(items)
    for n, (_, k, reason) in enumerate(scored):
        if n < max_keep:
            keep[k] = True
            reasons[reason] += 1
        else:
            reasons["over_cap"] += 1
    return keep, {**reasons, "_rejected": rejected}


def make_gate(max_keep: int = MAX_KEEP):
    """A gate for ingest.store_items(): loads readers' interests once, then decides."""
    async def gate(items: list[dict], vectors) -> tuple[list[bool], dict]:
        anchors, followed = load_interests()
        return decide(items, vectors, anchors, followed, max_keep)
    return gate
