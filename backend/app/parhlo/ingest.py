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


def merge_topics(d: "jev.ArticleDecision", hints: list[str]) -> list[str]:
    return list(dict.fromkeys([d.topic, *([d.second_topic] if d.second_topic else []), *hints]))[:3]


async def jev_backfill(hours: int = 48, limit: int = 600) -> dict:
    """Classify recent articles that were stored before Jev (or while Jev was unavailable)."""
    if not jev.enabled():
        return {"jev_backfilled": 0, "reason": "jev disabled"}
    with db() as conn:
        rows = conn.execute(
            """select id, title, rss_summary, source, topics from articles
               where jev_checked_at is null and fetched_at > now() - make_interval(hours => %s)
               order by published_at desc limit %s""", (hours, limit)).fetchall()
    decisions = await jev.classify_many(
        [{"title": r["title"], "excerpt": r["rss_summary"], "source": r["source"]} for r in rows])
    params = [(merge_topics(d, []), d.importance, d.junk, d.topic_confidence, r["id"])
              for r, d in zip(rows, decisions) if d]
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
    cutoff = datetime.now(timezone.utc) - MAX_AGE
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
        })
    return items


async def fetch_all(feeds: list[dict]) -> tuple[list[dict], list[str]]:
    errors: list[str] = []

    async def one(client: httpx.AsyncClient, feed: dict) -> list[dict]:
        try:
            r = await client.get(feed["url"])
            r.raise_for_status()
            return parse_feed(feed, r.content)
        except Exception as e:  # one bad feed must not stop the paper
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
            errors.append(f"{feed['name']} {feed['url']}: {type(e).__name__}")
            return []

    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={"User-Agent": UA}) as client:
        batches = await asyncio.gather(*(one(client, f) for f in feeds))
    seen, items = set(), []
    for item in (i for b in batches for i in b):
        if item["url"] not in seen:
            seen.add(item["url"])
            items.append(item)
    return items, errors


async def ingest(extra_queries: list[str] | None = None) -> dict:
    start = time.perf_counter()
    feeds = FEEDS + [google_news_feed(q) for q in (extra_queries or [])]
    items, errors = await fetch_all(feeds)

    with db() as conn:
        known = {r["url"] for r in conn.execute(
            "select url from articles where url = any(%s)", ([i["url"] for i in items],)
        )}
        # The same story can arrive twice from one outlet (direct feed + Google News fallback).
        seen_titles = {(r["source"], norm_title(r["title"])) for r in conn.execute(
            "select source, title from articles where fetched_at > now() - interval '3 days'")}
    new, batch_titles = [], set()
    for i in items:
        key = (i["source"], norm_title(i["title"]))
        if i["url"] in known or key in seen_titles or key in batch_titles:
            continue
        batch_titles.add(key)
        new.append(i)
    if not new:
        return {"fetched": len(items), "new": 0, "feeds": len(feeds), "errors": errors,
                "seconds": round(time.perf_counter() - start, 1)}

    vectors = await embed_texts([f"{i['title']}. {i['summary']}" for i in new])
    topics = await tag_topics(vectors, [i["hints"] for i in new])  # fallback tags (embedding similarity)
    decisions = await jev.classify_many(
        [{"title": i["title"], "excerpt": i["summary"], "source": i["source"]} for i in new])

    clustered = jev_done = junk = 0
    with db() as conn:
        for item, vec, tags, d in zip(new, vectors, topics, decisions):
            if d:  # Jev decided: its topic first, then a strong runner-up, then the feed's own hints
                tags = merge_topics(d, item["hints"])
                jev_done += 1
                junk += d.junk >= JUNK_THRESHOLD
            row = conn.execute(
                """insert into articles (url, source, source_region, title, rss_summary, image_url,
                                         published_at, topics, embedding, importance, junk, topic_confidence,
                                         jev_checked_at)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, case when %s then now() end)
                   on conflict (url) do nothing returning id""",
                (item["url"], item["source"], item["region"], item["title"], item["summary"],
                 item["image"], item["published"] or datetime.now(timezone.utc), tags, vec,
                 d.importance if d else None, d.junk if d else None, d.topic_confidence if d else None, d is not None),
            ).fetchone()
            if not row:
                continue
            # Same story from another outlet in the last 3 days? Join its cluster.
            near = conn.execute(
                """select coalesce(cluster_id, id) as cid, 1 - (embedding <=> %s) as sim from articles
                   where id <> %s and source <> %s and embedding is not null
                     and fetched_at > now() - interval '3 days'
                   order by embedding <=> %s limit 1""",
                (vec, row["id"], item["source"], vec),
            ).fetchone()
            cluster = near["cid"] if near and near["sim"] >= CLUSTER_SIM else row["id"]
            clustered += cluster != row["id"]
            conn.execute("update articles set cluster_id = %s where id = %s", (cluster, row["id"]))

    stats = {"fetched": len(items), "new": len(new), "joined_existing_story": clustered,
             "jev_classified": jev_done, "jev_junk": junk,
             "feeds": len(feeds), "errors": errors, "seconds": round(time.perf_counter() - start, 1)}
    log.info("ingest %s", stats)
    return stats
