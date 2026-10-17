"""② RANK — pick today's stories for one reader.

score = 0.40·best positive anchor match + 0.17·topic weight + 0.11·recency + 0.08·importance (Jev)
      + 0.05·story size + 0.08·source quality + 0.07·region fit + 0.05·source affinity
      − 0.55·best negative anchor match
then: drop Jev-flagged junk → one article per story cluster → 2 "common core" slots for the day's
biggest stories (Jev importance + outlet coverage) → MMR for variety → ~15% "discovery" slots.
"""

import math
import re
from datetime import datetime, timezone

import numpy as np

from app.core.database import db

CURATED = {"Dawn", "Express Tribune", "Business Recorder", "Geo News", "The News", "BBC News", "The Guardian",
           "The New York Times", "TechCrunch", "The Verge", "Ars Technica", "Hacker News", "ESPNcricinfo",
           "BBC Sport"}
KNOWN_GOOD = {"Reuters", "Associated Press", "AP News", "Al Jazeera", "CNN", "CNBC", "Bloomberg", "Financial Times",
              "The Economist", "Formula 1", "Motorsport.com", "The Race", "Sky Sports", "Wired", "MIT Technology Review",
              "The Times of India", "Hindustan Times", "Nature", "Science", "NPR", "The Washington Post",
              "Forbes", "Fortune", "Axios", "Politico", "Pakistan Today", "ARY News", "Samaa TV", "Arab News"}
BLOCKED_HINTS = ("kucoin", "bitget", "binance", "mexc", "coin", "crypto.news", "biggo", "prnewswire", "globenewswire")
STORIES_FOR_MINUTES = {5: 6, 10: 10, 15: 13, 20: 16}
JUNK_THRESHOLD = 0.78       # Jev: probability an item is not real news
CORE_SLOTS = 2              # day's biggest stories every reader gets
CORE_MIN_IMPORTANCE = 0.7   # Jev importance (0..1) needed to qualify for the core


def as_np(v) -> np.ndarray:
    """pgvector returns Vector objects; numpy needs plain arrays."""
    return v.to_numpy().astype(np.float32) if hasattr(v, "to_numpy") else np.asarray(v, dtype=np.float32)


def source_quality(source: str) -> float:
    s = source.lower()
    if any(h in s for h in BLOCKED_HINTS):
        return -1.0
    if source in CURATED:
        return 1.0
    return 0.8 if source in KNOWN_GOOD else 0.45


def story_count(minutes: int) -> int:
    best = min(STORIES_FOR_MINUTES, key=lambda m: abs(m - minutes))
    return STORIES_FOR_MINUTES[best]


def _words(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", title.lower())}


def same_story(a: str, b: str) -> bool:
    """Headline overlap check for stories two outlets worded differently (Jaccard ≥ 0.3 on 4+ letter words)."""
    wa, wb = _words(a), _words(b)
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.3


def rank_for_user(user: dict, exclude_ids: set[int] | None = None, hours: int = 36,
                  avoid_titles: list[str] | None = None, keep_ids: set[int] | None = None) -> list[dict]:
    """avoid_titles: headlines from the reader's previous paper, so yesterday's events don't come back reworded.
    keep_ids: stories the reader already engaged with in today's paper (a reprint keeps them eligible and favoured)."""
    exclude_ids = exclude_ids or set()
    keep_ids = keep_ids or set()
    avoid_titles = [t for t in (avoid_titles or []) if t]
    with db() as conn:
        prof = conn.execute("select topics, source_affinity from profiles where user_id=%s", (user["id"],)).fetchone()
        anchors = conn.execute("select label, weight, embedding from interest_anchors where user_id=%s",
                               (user["id"],)).fetchall()
        arts = conn.execute(
            """select a.id, a.title, a.source, a.source_region, a.topics, a.published_at, a.image_url,
                      a.url, a.rss_summary, a.cluster_id, a.embedding, a.importance, a.junk,
                      (select count(distinct b.source) from articles b where b.cluster_id = a.cluster_id) as cluster_size,
                      (select array_agg(distinct b.source) from articles b where b.cluster_id = a.cluster_id
                         and b.source <> a.source) as also_sources
               from articles a
               where a.embedding is not null and a.published_at > now() - make_interval(hours => %s)""",
            (hours,)).fetchall()
        # Already-seen stories (earlier editions) shouldn't repeat.
        seen = {r["article_id"] for r in conn.execute(
            "select distinct article_id from events where user_id=%s and article_id is not null", (user["id"],))}
    arts = [a for a in arts if a["id"] not in exclude_ids and (a["id"] not in seen or a["id"] in keep_ids)
            and source_quality(a["source"]) > 0 and len(re.findall(r"[A-Za-z]{3,}", a["title"])) >= 4
            and (a["junk"] or 0) < JUNK_THRESHOLD]
    if not arts:
        return []

    topics = (prof or {}).get("topics") or {}
    affinity = (prof or {}).get("source_affinity") or {}
    region_mix = float(user.get("region_mix", 0.5))
    now = datetime.now(timezone.utc)

    E = np.stack([as_np(a["embedding"]) for a in arts])
    pos = [a for a in anchors if a["weight"] > 0]
    neg = [a for a in anchors if a["weight"] < 0]

    def best_match(group):
        if not group:
            return np.zeros(len(arts)), [None] * len(arts)
        A = np.stack([as_np(g["embedding"]) for g in group])
        w = np.array([abs(g["weight"]) for g in group], dtype=np.float32)
        S = (E @ A.T) * np.minimum(w, 1.0)
        idx = S.argmax(axis=1)
        return S.max(axis=1), [group[i]["label"] for i in idx]

    pos_s, pos_label = best_match(pos)
    neg_s, _ = best_match(neg)

    scored = []
    for i, a in enumerate(arts):
        age_h = max(0.0, (now - a["published_at"]).total_seconds() / 3600)
        topic_w = max([topics.get(t, 0.1) for t in a["topics"]] or [0.1])
        region_fit = region_mix if a["source_region"] == "pakistan" else 1 - region_mix
        importance = a["importance"] if a["importance"] is not None else 0.4  # neutral until Jev has scored it
        score = (0.40 * pos_s[i] + 0.17 * topic_w + 0.11 * math.exp(-age_h / 24) + 0.08 * importance
                 + 0.05 * coverage(a["cluster_size"])
                 + 0.08 * source_quality(a["source"]) + 0.07 * region_fit
                 + 0.05 * float(affinity.get(a["source"], 0)) - 0.55 * neg_s[i]
                 - (0.04 if "news.google.com" in a["url"] else 0.0)  # prefer links we can read in full
                 + (0.15 if a["id"] in keep_ids else 0.0))
        scored.append({**a, "score": float(score), "match": pos_label[i], "match_sim": float(pos_s[i]),
                       "topic_weight": topic_w, "embedding": E[i], "importance": importance})

    # One article per story: keep the best-scoring version of each cluster.
    best_by_cluster: dict[int, dict] = {}
    for s in scored:
        key = s["cluster_id"] or s["id"]
        if key not in best_by_cluster or s["score"] > best_by_cluster[key]["score"]:
            best_by_cluster[key] = s
    # Outlets word the same event differently and embeddings don't always cluster them: keep the best version
    # of each event (headline overlap), and drop events already in the previous paper.
    pool: list[dict] = []
    for s in sorted(best_by_cluster.values(), key=lambda s: -s["score"]):
        if any(same_story(s["title"], t) for t in avoid_titles):
            continue
        if not any(same_story(s["title"], p["title"]) for p in pool):
            pool.append(s)
    return pool


def coverage(cluster_size: int | None) -> float:
    """0..1: how many outlets carried the story (1 outlet → 0, 6+ → 1)."""
    return min(1.0, math.log1p(max(0, (cluster_size or 1) - 1)) / math.log(6))


def core_score(p: dict) -> float:
    return 0.7 * (p.get("importance") or 0.0) + 0.3 * coverage(p.get("cluster_size"))


def select_stories(pool: list[dict], n: int, discovery_share: float = 0.15, n_core: int = CORE_SLOTS) -> list[dict]:
    """Common core (day's biggest stories) + personal picks (MMR for variety) + discovery outside the profile.

    The core answers readers' worry about missing important news (Reuters Institute: 48% worry about it).
    """
    core_candidates = sorted((p for p in pool if (p.get("importance") or 0) >= CORE_MIN_IMPORTANCE),
                             key=lambda p: -core_score(p))
    core = [{**p, "core": True} for p in mmr_by(core_candidates[:20], n_core, core_score)] if n >= 6 else []
    taken = {p["id"] for p in core}

    n_disc = max(1, round(n * discovery_share)) if n >= 6 else 0
    n_personal = n - len(core) - n_disc
    personal = mmr([p for p in pool if p["id"] not in taken and (p["topic_weight"] >= 0.3 or p["match_sim"] >= 0.35)],
                   n_personal, avoid=core)
    taken |= {p["id"] for p in personal}
    outside = [p for p in pool if p["id"] not in taken and p["topic_weight"] < 0.3]
    outside.sort(key=lambda p: -(core_score(p) + 0.5 * source_quality(p["source"])))
    discovery = [{**p, "discovery": True} for p in mmr(outside[:30], n_disc, avoid=core + personal)]
    taken |= {p["id"] for p in discovery}
    if len(personal) < n_personal:  # thin profile: top up from the general pool
        personal += [p for p in pool if p["id"] not in taken][: n_personal - len(personal)]
    return personal + core + discovery


def mmr(items: list[dict], k: int, lam: float = 0.72, avoid: list[dict] | None = None) -> list[dict]:
    return mmr_by(items, k, lambda c: c["score"], lam, avoid)


def mmr_by(items: list[dict], k: int, relevance, lam: float = 0.72, avoid: list[dict] | None = None) -> list[dict]:
    """Maximal marginal relevance: relevant, but not near-duplicates of what's already chosen (or `avoid`)."""
    chosen: list[dict] = []
    fixed = list(avoid or [])
    candidates = items[:120]
    while candidates and len(chosen) < k:
        def value(c):
            redundancy = max((float(c["embedding"] @ s["embedding"]) for s in chosen + fixed), default=0.0)
            return lam * relevance(c) - (1 - lam) * redundancy
        best = max(candidates, key=value)
        chosen.append(best)
        candidates.remove(best)
    return chosen
