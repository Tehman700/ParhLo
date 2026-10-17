"""Search the news: by meaning (pgvector) and by words (Postgres full text), in one query.

"Fuel prices" finds "Petrol cut by Rs3.93" (meaning); "Babar Azam" finds the exact name (words).
Results from the reader's own paper come first; topics they like rank a little higher; the same event from
several outlets shows once; junk and live-stream spam are filtered like in the paper.
"""

import re
import time
from collections import OrderedDict

from app.core.database import db
from app.parhlo.embed import embed_texts
from app.parhlo.rank import JUNK_THRESHOLD, SPAM, _overlap, _words, source_quality
from app.parhlo.topics import TOPICS

MIN_SEMANTIC = 0.30      # below this (and no word match) a result is unrelated
LIMIT = 12
_EMB_CACHE: OrderedDict[str, list[float]] = OrderedDict()  # repeated queries (typing, back/forward) skip the embed call

SQL = """
with q as (select %(emb)s::vector as e, websearch_to_tsquery('english', %(q)s) as tq)
select a.id, a.title, a.source, a.url, a.topics, a.published_at, a.image_url, a.source_region, a.cluster_id,
       coalesce(a.ai_summary, a.rss_summary) as summary,
       1 - (a.embedding <=> q.e) as sem,
       case when to_tsvector('english', a.title || ' ' || coalesce(a.rss_summary, '')) @@ q.tq
            then ts_rank(to_tsvector('english', a.title || ' ' || coalesce(a.rss_summary, '')), q.tq) else 0 end as kw
from articles a, q
where a.embedding is not null and a.published_at > now() - make_interval(days => %(days)s)
  and coalesce(a.junk, 0) < %(junk)s
  and (%(region)s::text is null or a.source_region = %(region)s)
order by (1 - (a.embedding <=> q.e)) + 0.6 * least(ts_rank(to_tsvector('english', a.title || ' ' || coalesce(a.rss_summary, '')), q.tq), 0.5) desc
limit 80
"""


async def _embed(q: str) -> list[float]:
    key = q.lower()
    if key in _EMB_CACHE:
        _EMB_CACHE.move_to_end(key)
        return _EMB_CACHE[key]
    vec = (await embed_texts([q]))[0].tolist()
    _EMB_CACHE[key] = vec
    if len(_EMB_CACHE) > 500:
        _EMB_CACHE.popitem(last=False)
    return vec


async def search(user: dict, q: str, days: int = 2, region: str | None = None) -> dict:
    t0 = time.perf_counter()
    q = re.sub(r"\s+", " ", q).strip()[:120]
    if len(q) < 2:
        return {"query": q, "results": [], "ms": 0}
    emb = await _embed(q)
    with db() as conn:
        rows = conn.execute(SQL, {"emb": emb, "q": q, "days": days, "junk": JUNK_THRESHOLD,
                                  "region": region if region in ("pakistan", "global") else None}).fetchall()
        prof = conn.execute("select topics, entities from profiles where user_id=%s", (user["id"],)).fetchone()
        paper = conn.execute("select data from editions where user_id=%s order by edition_date desc limit 1",
                             (user["id"],)).fetchone()
        saved = {r["article_id"] for r in conn.execute(
            "select article_id from article_state where user_id=%s and saved", (user["id"],)).fetchall()}
    topics = (prof or {}).get("topics") or {}
    in_paper = {s["id"]: s for s in (paper["data"]["stories"] if paper else [])}
    paper_words = {sid: _words(s["title"]) for sid, s in in_paper.items()}

    hits, kept_words, seen_clusters = [], [], set()
    for r in rows:
        sem, kw = float(r["sem"]), float(r["kw"] or 0)
        if (sem < MIN_SEMANTIC and kw <= 0) or SPAM.search(r["title"]) or source_quality(r["source"]) <= 0:
            continue
        if r["cluster_id"] and r["cluster_id"] in seen_clusters:
            continue
        w = _words(r["title"])
        if any(_overlap(w, k) for k in kept_words):  # same event, another outlet
            continue
        paper_id = r["id"] if r["id"] in in_paper else next((sid for sid, pw in paper_words.items() if _overlap(w, pw)), None)
        like = max([topics.get(t, 0.1) for t in (r["topics"] or [])] or [0.1])
        score = sem + 0.6 * min(kw, 0.5) + 0.05 * like + (0.15 if paper_id else 0)
        seen_clusters.add(r["cluster_id"])
        kept_words.append(w)
        hits.append({
            "id": r["id"], "title": r["title"], "source": r["source"], "url": r["url"], "image": r["image_url"],
            "published_at": r["published_at"].isoformat() if r["published_at"] else None,
            "topic": TOPICS.get((r["topics"] or [""])[0], {}).get("label"),
            "summary": (r["summary"] or "")[:240], "in_paper": paper_id is not None, "paper_story_id": paper_id,
            "saved": r["id"] in saved, "score": round(score, 3),
        })
    hits.sort(key=lambda h: -h["score"])
    hits = hits[:LIMIT]
    followed = {e.lower() for e in ((prof or {}).get("entities") or [])}
    # A short name-like query can become an interest with one tap ("Follow Nvidia").
    can_follow = 1 <= len(q.split()) <= 4 and q.lower() not in followed and bool(hits)
    return {"query": q, "results": hits, "can_follow": can_follow, "ms": round((time.perf_counter() - t0) * 1000)}
