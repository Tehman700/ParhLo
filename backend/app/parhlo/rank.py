"""② RANK — pick today's stories for one reader.

score = 0.42·best positive anchor match  + 0.18·topic weight + 0.12·recency + 0.08·story size
      + 0.08·source quality + 0.07·region fit + 0.05·source affinity − 0.55·best negative anchor match
then: one article per story cluster → MMR for variety → ~15% "discovery" slots outside the profile.
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


def rank_for_user(user: dict, exclude_ids: set[int] | None = None, hours: int = 36) -> list[dict]:
    exclude_ids = exclude_ids or set()
    with db() as conn:
        prof = conn.execute("select topics, source_affinity from profiles where user_id=%s", (user["id"],)).fetchone()
        anchors = conn.execute("select label, weight, embedding from interest_anchors where user_id=%s",
                               (user["id"],)).fetchall()
        arts = conn.execute(
            """select a.id, a.title, a.source, a.source_region, a.topics, a.published_at, a.image_url,
                      a.url, a.rss_summary, a.cluster_id, a.embedding,
                      (select count(distinct b.source) from articles b where b.cluster_id = a.cluster_id) as cluster_size,
                      (select array_agg(distinct b.source) from articles b where b.cluster_id = a.cluster_id
                         and b.source <> a.source) as also_sources
               from articles a
               where a.embedding is not null and a.published_at > now() - make_interval(hours => %s)""",
            (hours,)).fetchall()
        # Already-seen stories (earlier editions) shouldn't repeat.
        seen = {r["article_id"] for r in conn.execute(
            "select distinct article_id from events where user_id=%s and article_id is not null", (user["id"],))}
    arts = [a for a in arts if a["id"] not in exclude_ids and a["id"] not in seen
            and source_quality(a["source"]) > 0 and len(re.findall(r"[A-Za-z]{3,}", a["title"])) >= 4]
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
        score = (0.42 * pos_s[i] + 0.18 * topic_w + 0.12 * math.exp(-age_h / 24)
                 + 0.08 * min(1.0, math.log1p(a["cluster_size"] or 1) / math.log(6))
                 + 0.08 * source_quality(a["source"]) + 0.07 * region_fit
                 + 0.05 * float(affinity.get(a["source"], 0)) - 0.55 * neg_s[i]
                 - (0.04 if "news.google.com" in a["url"] else 0.0))  # prefer links we can read in full
        scored.append({**a, "score": float(score), "match": pos_label[i], "match_sim": float(pos_s[i]),
                       "topic_weight": topic_w, "embedding": E[i]})

    # One article per story: keep the best-scoring version of each cluster.
    best_by_cluster: dict[int, dict] = {}
    for s in scored:
        key = s["cluster_id"] or s["id"]
        if key not in best_by_cluster or s["score"] > best_by_cluster[key]["score"]:
            best_by_cluster[key] = s
    pool, seen_titles = [], set()
    for s in sorted(best_by_cluster.values(), key=lambda s: -s["score"]):
        key = re.sub(r"[^a-z0-9]+", " ", s["title"].lower()).strip()
        if key not in seen_titles:  # same headline via two URLs
            seen_titles.add(key)
            pool.append(s)
    return pool


def select_stories(pool: list[dict], n: int, discovery_share: float = 0.15) -> list[dict]:
    """MMR for variety among personal picks + a few high-signal stories from outside the profile."""
    n_disc = max(1, round(n * discovery_share)) if n >= 6 else 0
    personal = mmr([p for p in pool if p["topic_weight"] >= 0.3 or p["match_sim"] >= 0.35], n - n_disc)
    chosen_ids = {p["id"] for p in personal}
    outside = [p for p in pool if p["id"] not in chosen_ids and p["topic_weight"] < 0.3]
    outside.sort(key=lambda p: -((p["cluster_size"] or 1) + 2 * source_quality(p["source"])))
    discovery = [{**p, "discovery": True} for p in mmr(outside[:30], n_disc)]
    if len(personal) < n - n_disc:  # thin profile: top up from the general pool
        rest = [p for p in pool if p["id"] not in chosen_ids and p["id"] not in {d["id"] for d in discovery}]
        personal += rest[: n - n_disc - len(personal)]
    return personal + discovery


def mmr(items: list[dict], k: int, lam: float = 0.72) -> list[dict]:
    chosen: list[dict] = []
    candidates = items[:120]
    while candidates and len(chosen) < k:
        def value(c):
            redundancy = max((float(c["embedding"] @ s["embedding"]) for s in chosen), default=0.0)
            return lam * c["score"] - (1 - lam) * redundancy
        best = max(candidates, key=value)
        chosen.append(best)
        candidates.remove(best)
    return chosen
