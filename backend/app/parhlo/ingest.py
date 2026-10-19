"""① INGEST — shared by all readers.

feeds (+ Google News per interest) → parse → skip known URLs → insert → embed title+summary
→ tag topics → cluster with same-story coverage from other outlets.
Full text + AI summary are produced lazily, only for articles that land in a paper (see summarize.py).
"""

import asyncio
import html
import logging
import re
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone

import feedparser
import httpx

from app.core.database import db
from app.parhlo import jev
from app.parhlo.embed import embed_texts, tag_topics
from app.parhlo.sources import FEEDS, google_news_feed, google_news_site

log = logging.getLogger("parhlo.ingest")
UA = "Mozilla/5.0 (compatible; ParhLo/1.0; +https://github.com/Tehman700/ParhLo)"
MAX_AGE = timedelta(hours=48)
CLUSTER_SIM = 0.84  # cosine similarity above which two articles are "the same story"
JUNK_THRESHOLD = 0.78  # Jev: probability the item is not real news (quiz, podcast, promo, tag page…)


# With no general "other sports" topic, horse racing lands closest to motorsport; keep it out of Formula 1 readers' papers.
NOT_MOTORSPORT = re.compile(r"horse|racecourse|jockey|caulfield|the everest|melbourne cup|thoroughbred|greyhound|derby day", re.I)


# ── INGEST STEP 8 (helper) ── Decide an article's final topics (at most 3), in priority order:
#   1. Jev's chosen topic            (most reliable: it read the headline + excerpt)
#   2. Jev's runner-up, if strong    (second_topic is set only when its probability ≥ 0.25, e.g. "economy" + "business")
#   3. the feed's own hints          (a cricket feed → "cricket")
# dict.fromkeys removes duplicates but keeps that order. Then a guard: horse racing is never "motorsport"
# (Jev has no "other sports" topic, so it picked the closest one — this stops it reaching Formula 1 readers).
def merge_topics(d: "jev.ArticleDecision", hints: list[str], title: str = "") -> list[str]:
    topics = list(dict.fromkeys([d.topic, *([d.second_topic] if d.second_topic else []), *hints]))[:3]
    if "motorsport" in topics and NOT_MOTORSPORT.search(title):
        topics = [t for t in topics if t != "motorsport"]
    return topics


# ── INGEST STEP 11 ── Catch-up: classify recent articles Jev has NOT checked yet.
# Why needed: if Jev was down or timed out during STEP 7, those articles were stored with fallback tags only
# (jev_checked_at is NULL). This finds them (last 48 h, up to 600) and fills in topic, importance and junk,
# so no article stays unclassified for long. Called by the nightly cron right after ingest().
async def jev_backfill(hours: int = 48, limit: int = 600) -> dict:
    """Classify recent articles that were stored before Jev (or while Jev was unavailable)."""
    if not jev.enabled():
        return {"jev_backfilled": 0, "reason": "jev disabled"}
    with db() as conn:
        # Articles Jev never checked, newest first.
        rows = conn.execute(
            """select id, title, rss_summary, source, topics from articles
               where jev_checked_at is null and fetched_at > now() - make_interval(hours => %s)
               order by published_at desc limit %s""", (hours, limit)).fetchall()
    # Same call as STEP 7: 12 articles at a time.
    decisions = await jev.classify_many(
        [{"title": r["title"], "excerpt": r["rss_summary"], "source": r["source"]} for r in rows])
    # Build one UPDATE row per article Jev answered (skip the ones it still couldn't do; they're retried next run).
    params = [(merge_topics(d, [], r["title"]), d.importance, d.junk, d.topic_confidence, r["id"])
              for r, d in zip(rows, decisions) if d]
    # executemany = all updates in one round trip to the database (fast even for hundreds of rows).
    with db() as conn, conn.cursor() as cur:
        cur.executemany(
            """update articles set topics = %s, importance = %s, junk = %s, topic_confidence = %s,
               jev_checked_at = now() where id = %s""", params)
    done = len(params)
    junk = sum(1 for p in params if p[2] >= JUNK_THRESHOLD)
    return {"jev_backfilled": done, "jev_backfill_junk": junk, "pending": len(rows) - done}


def norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def clean_text(raw: str | None, limit: int = 600) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return "" if re.fullmatch(r"https?://\S+", text) else text[:limit]  # some feeds put a bare URL here


def _image(entry) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key) or []:
            if m.get("url"):
                return m["url"]
    for link in entry.get("links") or []:
        if link.get("type", "").startswith("image/") and link.get("href"):
            return link["href"]
    match = re.search(r'<img[^>]+src="([^"]+)"', entry.get("summary", "") or "")
    return match.group(1) if match else None


def _published(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc) if parsed else None


def parse_feed(feed: dict, body: bytes) -> list[dict]:
    parsed = feedparser.parse(body)
    # 48 hours by default; a feed can ask for more (e.g. a 7-day Google News search for a question in Ask).
    cutoff = datetime.now(timezone.utc) - max(MAX_AGE, timedelta(hours=feed.get("max_age_hours", 0)))
    items = []
    for e in parsed.entries:
        url, title = e.get("link"), clean_text(e.get("title"), 300)
        if not url or not title:
            continue
        published = _published(e)
        if published and published < cutoff:
            continue
        source = feed["name"]
        if feed["name"] == "Google News" or feed.get("outlet"):  # "Headline - Outlet" → real outlet name
            outlet = (e.get("source") or {}).get("title")
            if outlet:
                source = outlet
                title = re.sub(rf"\s+-\s+{re.escape(outlet)}$", "", title)
        if len(re.findall(r"[A-Za-z]{3,}", title)) < 4:  # section pages like "Business & Finance - Dawn"
            continue
        items.append({
            "url": url, "title": title, "source": source, "region": feed["region"],
            "summary": clean_text(e.get("summary") or e.get("description")),
            "image": _image(e), "published": published, "hints": feed["topics"],
            # SWS: where the story came from, and the country edition / language it was found in (if known).
            "origin": feed.get("origin", "rss"), "country": feed.get("country"), "language": feed.get("language", "en"),
        })
    return items


# ── INGEST STEP 3 ── Fetch every feed IN PARALLEL (28 RSS feeds + Google News searches for followed names).
# Returns (items, errors): items = every story from every feed (de-duplicated by URL), errors = which feeds failed.
async def fetch_all(feeds: list[dict]) -> tuple[list[dict], list[str]]:
    errors: list[str] = []

    # Fetches ONE feed. Runs once per feed, all at the same time (see asyncio.gather below).
    async def one(client: httpx.AsyncClient, feed: dict) -> list[dict]:
        try:
            r = await client.get(feed["url"])          # download the RSS XML
            r.raise_for_status()                        # 4xx/5xx → treat as a failure (go to except)
            return parse_feed(feed, r.content)          # XML → list of clean story dicts
        except Exception as e:  # one bad feed must not stop the paper
            # Graceful degradation: Dawn blocks Vercel's cloud IPs, so its direct feed fails in production.
            # For feeds with a "fallback", fetch the SAME outlet's stories through Google News instead.
            if feed.get("fallback"):  # outlet blocks us (e.g. cloud IPs) → its stories via Google News
                domain, extra = feed["fallback"]
                try:
                    fb = google_news_site(domain, feed["name"], feed["region"], feed["topics"], extra)
                    r = await client.get(fb["url"])
                    r.raise_for_status()
                    errors.append(f"{feed['name']} {feed['url']}: {type(e).__name__} → used Google News fallback")
                    return parse_feed(fb, r.content)
                except Exception:
                    pass
            # Record the failure (returned in the cron's JSON report) and carry on with the other feeds.
            errors.append(f"{feed['name']} {feed['url']}: {type(e).__name__}")
            return []

    # One shared HTTP client (connection reuse), 15 s timeout per feed, a polite User-Agent naming ParhLo.
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={"User-Agent": UA}) as client:
        # asyncio.gather = all feeds download concurrently, so the whole fetch takes about as long as the slowest feed.
        batches = await asyncio.gather(*(one(client, f) for f in feeds))
    # Flatten the per-feed lists into one list, dropping exact duplicate URLs (same story in two feeds).
    seen, items = set(), []
    for item in (i for b in batches for i in b):
        if item["url"] not in seen:
            seen.add(item["url"])
            items.append(item)
    return items, errors


# The main ingest pipeline, called by the nightly cron (STEP 1). Runs STEPS 3 → 10 in order.
async def ingest(extra_queries: list[str] | None = None) -> dict:
    start = time.perf_counter()
    # The 28 curated feeds + one Google News search feed per followed name (STEP 2).
    feeds = FEEDS + [google_news_feed(q) for q in (extra_queries or [])]
    # STEP 3: download everything in parallel.
    items, errors = await fetch_all(feeds)
    # STEPS 4–10: skip known → embed → Jev → topics → store → cluster (shared with SWS, see store_items).
    stats = await store_items(items)
    stats = {"fetched": len(items), **stats, "feeds": len(feeds), "errors": errors,
             "seconds": round(time.perf_counter() - start, 1)}
    log.info("ingest %s", stats)
    return stats


# A gate decides, after embedding and BEFORE the paid steps (Jev, summaries), which new items are worth keeping.
# It returns one bool per item, plus a report of why items were dropped. SWS uses it; the nightly RSS run doesn't.
Gate = Callable[[list[dict], list], Awaitable[tuple[list[bool], dict]]]


# STEPS 4–10 for any list of items in the parse_feed() shape: RSS, Google News, GDELT or web search (SWS).
# Returns counts: new, kept (after the gate), joined_existing_story, jev_classified, jev_junk (+ the gate's report).
async def store_items(items: list[dict], gate: Gate | None = None) -> dict:
    # ── INGEST STEPS 4–5 ── Skip what we already have: the same URL, or the same headline from the same outlet
    # in the last 3 days (the same story can arrive twice from one outlet: direct feed + Google News fallback).
    with db() as conn:
        known = {r["url"] for r in conn.execute(
            "select url from articles where url = any(%s)", ([i["url"] for i in items],)
        )}
        seen_titles = {(r["source"], norm_title(r["title"])) for r in conn.execute(
            "select source, title from articles where fetched_at > now() - interval '3 days'")}
    new, batch_titles = [], set()
    for i in items:
        key = (i["source"], norm_title(i["title"]))
        if i["url"] in known or key in seen_titles or key in batch_titles:
            continue
        batch_titles.add(key)
        new.append(i)
    stats: dict = {"new": len(new), "kept": 0, "joined_existing_story": 0, "jev_classified": 0, "jev_junk": 0}
    if not new:
        return stats

    # ── INGEST STEP 6 ── Embed each NEW article ONCE (OpenAI text-embedding-3-small, 1536 numbers per article).
    # We embed "title. summary" — enough meaning to match readers' interests. The vector is stored on the article
    # (STEP 9) and SHARED by every reader: ranking, search, "more like this" and clustering all reuse it.
    # Only `new` articles are embedded (already-stored ones were skipped above), so we never pay twice.
    # (GDELT items have no summary, so they're embedded by their headline alone.)
    vectors = await embed_texts([f"{i['title']}. {i['summary']}" if i.get("summary") else i["title"] for i in new])

    # SWS gate (optional): drop items no reader would get BEFORE the paid steps below (Jev, and later summaries).
    if gate:
        keep, report = await gate(new, vectors)
        stats["gate"] = report
        new = [i for i, k in zip(new, keep) if k]
        vectors = vectors[[n for n, k in enumerate(keep) if k]]
        if not new:
            return stats
    stats["kept"] = len(new)

    # Fallback topic tags from vectors alone (closest topic descriptions) — used only if Jev fails (see embed.py).
    topics = await tag_topics(vectors, [i["hints"] for i in new])  # fallback tags (embedding similarity)

    # ── INGEST STEP 7 ── Jev classifies every new article (12 at a time, see jev.py → classify_many):
    #   topic      (Choice: which of our 17 topics?)
    #   junk       (Noul:   probability it is NOT real news — quiz, podcast listing, promo, tag page…)
    #   importance (Score:  trivial → major, for a general reader in Pakistan today)
    # Returns one decision per article in the same order, or None where Jev failed (then the fallback tags are kept).
    decisions = await jev.classify_many(
        [{"title": i["title"], "excerpt": i["summary"], "source": i["source"]} for i in new])

    with db() as conn:
        # Walk the four parallel lists together: the article, its vector, its fallback tags, Jev's decision.
        for item, vec, tags, d in zip(new, vectors, topics, decisions):
            # ── INGEST STEP 8 ── Final topics: Jev's topic first, a strong runner-up, then the feed's own hints
            # (merge_topics at the top of this file also removes "motorsport" from horse-racing stories).
            if d:  # Jev decided: its topic first, then a strong runner-up, then the feed's own hints
                tags = merge_topics(d, item["hints"], item["title"])
                stats["jev_classified"] += 1
                stats["jev_junk"] += d.junk >= JUNK_THRESHOLD   # counted for the report; junk is stored but never shown
            # ── INGEST STEP 9 ── Store the article in Postgres, WITH its vector and Jev's decisions.
            # This row is the shared "cache": every reader's paper, search and Ask read from it — nothing is
            # recomputed per reader. `on conflict (url) do nothing` makes it safe if two runs overlap.
            # `jev_checked_at` is set only when Jev answered, so STEP 11 can find the ones it missed.
            # origin / country / language say where SWS found it (curated RSS: "rss", country unknown, "en").
            row = conn.execute(
                """insert into articles (url, source, source_region, title, rss_summary, image_url,
                                         published_at, topics, embedding, importance, junk, topic_confidence,
                                         jev_checked_at, origin, country, language, content)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, case when %s then now() end, %s,%s,%s,%s)
                   on conflict (url) do nothing returning id""",
                (item["url"], item["source"], item["region"], item["title"], item["summary"],
                 item["image"], item["published"] or datetime.now(timezone.utc), tags, vec,
                 d.importance if d else None, d.junk if d else None, d.topic_confidence if d else None, d is not None,
                 item.get("origin", "rss"), item.get("country"), item.get("language"), item.get("content")),
            ).fetchone()
            if not row:
                continue   # already existed (another run inserted it first) → nothing more to do
            # ── INGEST STEP 10 ── Cluster: is this the SAME EVENT another outlet already reported?
            # pgvector query: find the single closest article (by meaning) from a DIFFERENT outlet in the last
            # 3 days. `<=>` is cosine distance, so `1 - distance` = similarity (1.0 = identical meaning).
            # The HNSW index on articles.embedding makes this nearest-neighbour search fast.
            near = conn.execute(
                """select coalesce(cluster_id, id) as cid, 1 - (embedding <=> %s) as sim from articles
                   where id <> %s and source <> %s and embedding is not null
                     and fetched_at > now() - interval '3 days'
                   order by embedding <=> %s limit 1""",
                (vec, row["id"], item["source"], vec),
            ).fetchone()
            # Similar enough (≥ 0.84) → join that story's cluster; otherwise this article starts its own cluster.
            # Later, ranking keeps only the best article per cluster, so a reader sees each event ONCE, and
            # cluster size (how many outlets ran it) feeds the "Top story" importance.
            cluster = near["cid"] if near and near["sim"] >= CLUSTER_SIM else row["id"]
            stats["joined_existing_story"] += cluster != row["id"]
            conn.execute("update articles set cluster_id = %s where id = %s", (cluster, row["id"]))
    return stats
