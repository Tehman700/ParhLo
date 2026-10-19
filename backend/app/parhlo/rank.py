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
from app.parhlo.sws.outlets import WORLD_GOOD

CURATED = {"Dawn", "Express Tribune", "Business Recorder", "Geo News", "The News", "BBC News", "The Guardian",
           "The New York Times", "TechCrunch", "The Verge", "Ars Technica", "Hacker News", "ESPNcricinfo",
           "BBC Sport"}
KNOWN_GOOD = {"Reuters", "Associated Press", "AP News", "Al Jazeera", "CNN", "CNBC", "Bloomberg", "Financial Times",
              "The Economist", "Formula 1", "Motorsport.com", "The Race", "Sky Sports", "Wired", "MIT Technology Review",
              "The Times of India", "Hindustan Times", "Nature", "Science", "NPR", "The Washington Post",
              "Forbes", "Fortune", "Axios", "Politico", "Pakistan Today", "ARY News", "Samaa TV", "Arab News"}
KNOWN_GOOD |= WORLD_GOOD  # established outlets worldwide (SWS brings their stories in)
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


OFF_WEIGHT = 0.05  # a topic switched off on the dashboard
# "[WATCH LIVE] … live stream free" pages that slip through feeds and search results
SPAM = re.compile(r"live\s*-?\s*stream|watch\s*live|livestream|\[watch|【live|\blive free\b|\bstream(ing)? free\b", re.I)


def _words(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", title.lower())}


def _overlap(wa: set[str], wb: set[str]) -> bool:
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.3


def same_story(a: str, b: str) -> bool:
    """Headline overlap check for stories two outlets worded differently (Jaccard ≥ 0.3 on 4+ letter words)."""
    return _overlap(_words(a), _words(b))


POOL_MAX = 150  # candidates kept for selection (best personal scores + biggest stories + discovery material)

# Interest matching runs in Postgres (pgvector): only scores travel, not ~1,300 × 1,536-float embeddings.
# Vectors are converted once to halfvec in the CTEs: each stored vector is unpacked once instead of once per
# reader memory (324 ms → 103 ms on 1,560 candidates × 22 memories, identical ranking). SWS adds thousands of
# stories a day, so candidates are capped at the newest CANDIDATE_CAP to keep the worst case about a second.
CANDIDATE_CAP = 4000
RANK_SQL = """
with cand as (
  select a.id, a.title, a.source, a.source_region, a.topics, a.published_at, a.image_url, a.url, a.rss_summary,
         a.cluster_id, a.importance, a.embedding::halfvec(1536) as embedding, a.language, a.country
  from articles a
  where a.embedding is not null and a.published_at > now() - make_interval(hours => %(hours)s)
    and coalesce(a.junk, 0) < %(junk)s
  order by a.published_at desc limit %(cap)s
),
cl as (
  select cluster_id, count(distinct source) as cluster_size, array_agg(distinct source) as sources
  from articles where cluster_id in (select cluster_id from cand where cluster_id is not null)
  group by cluster_id
),
anc as (select label, kind, weight, embedding::halfvec(1536) as embedding from interest_anchors where user_id = %(uid)s),
pos as (
  select distinct on (c.id) c.id, (1 - (c.embedding <=> anc.embedding)) * least(anc.weight, 1) as s, anc.label, anc.kind
  from cand c cross join anc where anc.weight > 0
  order by c.id, (1 - (c.embedding <=> anc.embedding)) * least(anc.weight, 1) desc
),
neg as (
  select c.id, max((1 - (c.embedding <=> anc.embedding)) * least(-anc.weight, 1)) as s
  from cand c cross join anc where anc.weight < 0 group by c.id
)
select c.id, c.title, c.source, c.source_region, c.topics, c.published_at, c.image_url, c.url, c.rss_summary,
       c.cluster_id, c.importance, c.language, c.country, coalesce(cl.cluster_size, 0) as cluster_size, cl.sources,
       coalesce(pos.s, 0) as pos_s, pos.label as pos_label, pos.kind as pos_kind, coalesce(neg.s, 0) as neg_s
from cand c left join cl on cl.cluster_id = c.cluster_id left join pos on pos.id = c.id left join neg on neg.id = c.id
"""


def rank_for_user(user: dict, exclude_ids: set[int] | None = None, hours: int = 36,
                  avoid_titles: list[str] | None = None) -> list[dict]:
    """avoid_titles: headlines from the reader's previous paper, so yesterday's events don't come back reworded."""
    exclude_ids = exclude_ids or set()
    avoid_words = [w for w in (_words(t) for t in (avoid_titles or []) if t) if w]
    with db() as conn:
        prof = conn.execute("select topics, source_affinity from profiles where user_id=%s", (user["id"],)).fetchone()
        arts = conn.execute(RANK_SQL, {"hours": hours, "junk": JUNK_THRESHOLD, "uid": user["id"],
                                       "cap": CANDIDATE_CAP}).fetchall()
        # Already-seen stories (earlier editions) shouldn't repeat.
        seen = {r["article_id"] for r in conn.execute(
            "select distinct article_id from events where user_id=%s and article_id is not null", (user["id"],))}
        follows = followed_terms(conn, user["id"])
        found_for = {}
        if follows:
            for r in conn.execute("select article_id, term from article_terms where term = any(%s) "
                                  "and article_id = any(%s)", (list(follows), [a["id"] for a in arts])).fetchall():
                found_for.setdefault(r["article_id"], follows[r["term"]])
    arts = [a for a in arts if a["id"] not in exclude_ids and a["id"] not in seen and not SPAM.search(a["title"])
            and source_quality(a["source"]) > 0 and len(re.findall(r"[A-Za-z]{3,}", a["title"])) >= 4]
    if not arts:
        return []

    topics = (prof or {}).get("topics") or {}
    affinity = (prof or {}).get("source_affinity") or {}
    region_mix = float(user.get("region_mix", 0.5))
    now = datetime.now(timezone.utc)

    scored = []
    for a in arts:
        age_h = max(0.0, (now - a["published_at"]).total_seconds() / 3600)
        topic_w = max([topics.get(t, 0.1) for t in a["topics"]] or [0.1])
        region_fit = region_mix if a["source_region"] == "pakistan" else 1 - region_mix
        importance = a["importance"] if a["importance"] is not None else 0.4  # neutral until Jev has scored it
        pos_s, neg_s = float(a["pos_s"]), float(a["neg_s"])
        # Found by searching for something the reader follows (or about a country they follow): a certain match,
        # even when the topic is broad/off or the headline is far from the phrase in embedding space.
        followed = found_for.get(a["id"]) or follows.get((a.get("country") or "").lower())
        if followed:
            pos_s, topic_w = max(pos_s, FOLLOWED_MATCH), max(topic_w, 0.8)
        score = (0.40 * pos_s + 0.17 * topic_w + 0.11 * math.exp(-age_h / 24) + 0.08 * importance
                 + 0.05 * coverage(a["cluster_size"])
                 + 0.08 * source_quality(a["source"]) + 0.07 * region_fit
                 + 0.05 * float(affinity.get(a["source"], 0)) - 0.55 * neg_s
                 - (0.04 if "news.google.com" in a["url"] else 0.0))  # prefer links we can read in full
        also = [x for x in (a["sources"] or []) if x != a["source"]]
        match = followed or (a["pos_label"] if a["pos_kind"] in ("onboarding", "entity") else None)
        scored.append({**a, "also_sources": also, "score": float(score), "match": match, "match_sim": pos_s,
                       "topic_weight": topic_w, "importance": importance})

    # One article per story: keep the best-scoring version of each cluster.
    best_by_cluster: dict[int, dict] = {}
    for s in scored:
        key = s["cluster_id"] or s["id"]
        if key not in best_by_cluster or s["score"] > best_by_cluster[key]["score"]:
            best_by_cluster[key] = s
    ranked = sorted(best_by_cluster.values(), key=lambda s: -s["score"])
    # Only these can be chosen: the best personal scores, the day's biggest stories, and discovery material.
    keep = {s["id"] for s in ranked[:110]}
    keep |= {s["id"] for s in sorted(ranked, key=lambda s: -core_score(s))[:40]}
    keep |= {s["id"] for s in sorted((s for s in ranked if OFF_WEIGHT < s["topic_weight"] < 0.3),
                                     key=lambda s: -(core_score(s) + 0.5 * source_quality(s["source"])))[:40]}
    # Outlets word the same event differently and embeddings don't always cluster them: keep the best version
    # of each event (headline overlap), and drop events already in the previous paper.
    pool: list[dict] = []
    kept_words: list[set[str]] = []
    for s in ranked:
        if s["id"] not in keep:
            continue
        w = _words(s["title"])
        if any(_overlap(w, aw) for aw in avoid_words) or any(_overlap(w, kw) for kw in kept_words):
            continue
        pool.append(s)
        kept_words.append(w)
        if len(pool) >= POOL_MAX:
            break
    # Embeddings only for the pool (MMR variety in select_stories needs them).
    with db() as conn:
        emb = {r["id"]: as_np(r["embedding"]) for r in conn.execute(
            "select id, embedding from articles where id = any(%s)", ([p["id"] for p in pool],)).fetchall()}
    for p in pool:
        p["embedding"] = emb[p["id"]]
    return pool


FOLLOWED_MATCH = 0.6   # interest-match score for a story found by searching for a followed term


def followed_terms(conn, user_id) -> dict[str, str]:
    """What the reader follows (names) and wrote in "About you" (phrases): lower-case → as they wrote it."""
    from app.parhlo.sws.planner import interest_phrases
    prof = conn.execute("select entities from profiles where user_id=%s", (user_id,)).fetchone() or {}
    terms = {e.strip().lower(): e.strip() for e in (prof.get("entities") or []) if e and e.strip()}
    for phrase in interest_phrases(conn, user_id):
        terms.setdefault(phrase, phrase)
    return terms


def coverage(cluster_size: int | None) -> float:
    """0..1: how many outlets carried the story (1 outlet → 0, 6+ → 1)."""
    return min(1.0, math.log1p(max(0, (cluster_size or 1) - 1)) / math.log(6))


def core_score(p: dict) -> float:
    return 0.7 * (p.get("importance") or 0.0) + 0.3 * coverage(p.get("cluster_size"))


def cover_topics(personal: list[dict], pool: list[dict], taken: set[int], on_topics: list[str]) -> list[dict]:
    """Every topic the reader has switched on gets at least one personal story when the pool has one:
    the best story of a missing topic replaces the weakest pick from a topic that has more than one."""
    personal = list(personal)
    for topic in on_topics:
        if any(p["topics"] and p["topics"][0] == topic for p in personal):
            continue
        cand = next((p for p in pool if p["id"] not in taken and p["topics"] and p["topics"][0] == topic), None)
        counts: dict[str, int] = {}
        for p in personal:
            counts[p["topics"][0] if p["topics"] else ""] = counts.get(p["topics"][0] if p["topics"] else "", 0) + 1
        spare = [p for p in personal if counts[p["topics"][0] if p["topics"] else ""] > 1]
        if not cand or not spare:
            continue
        out = min(spare, key=lambda p: p["score"])
        personal[personal.index(out)] = cand
        taken.discard(out["id"])
        taken.add(cand["id"])
    return personal


def select_stories(pool: list[dict], n: int, discovery_share: float = 0.15, n_core: int = CORE_SLOTS,
                   on_topics: list[str] | None = None) -> list[dict]:
    """Common core (day's biggest stories) + personal picks (MMR for variety) + discovery outside the profile.

    The core answers readers' worry about missing important news (Reuters Institute: 48% worry about it).
    """
    core_candidates = sorted((p for p in pool if (p.get("importance") or 0) >= CORE_MIN_IMPORTANCE),
                             key=lambda p: -core_score(p))
    core = [{**p, "core": True} for p in mmr_by(core_candidates[:20], n_core, core_score)] if n >= 6 else []
    taken = {p["id"] for p in core}

    n_disc = max(1, round(n * discovery_share)) if n >= 6 else 0
    n_personal = n - len(core) - n_disc
    personal = mmr([p for p in pool if p["id"] not in taken and p["topic_weight"] > OFF_WEIGHT
                    and (p["topic_weight"] >= 0.3 or p["match_sim"] >= 0.35)],
                   n_personal, avoid=core)
    taken |= {p["id"] for p in personal}
    if on_topics:
        personal = cover_topics(personal, pool, taken, on_topics)
    # "Something new" comes from outside the reader's interests, but never from topics they switched off (0.05).
    outside = [p for p in pool if p["id"] not in taken and OFF_WEIGHT < p["topic_weight"] < 0.3]
    outside.sort(key=lambda p: -(core_score(p) + 0.5 * source_quality(p["source"])))
    discovery = [{**p, "discovery": True} for p in mmr(outside[:30], n_disc, avoid=core + personal)]
    taken |= {p["id"] for p in discovery}
    if len(personal) < n_personal:  # thin profile: top up from the general pool
        personal += [p for p in pool if p["id"] not in taken and p["topic_weight"] > OFF_WEIGHT][: n_personal - len(personal)]
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
