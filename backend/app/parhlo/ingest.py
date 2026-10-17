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
from app.parhlo.embed import embed_texts, tag_topics
from app.parhlo.sources import FEEDS, google_news_feed

log = logging.getLogger("parhlo.ingest")
UA = "Mozilla/5.0 (compatible; ParhLo/1.0; +https://github.com/Tehman700/ParhLo)"
MAX_AGE = timedelta(hours=48)
CLUSTER_SIM = 0.84  # cosine similarity above which two articles are "the same story"


def clean_text(raw: str | None, limit: int = 600) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


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
        if feed["name"] == "Google News":  # "Headline - Outlet" → real outlet name
            outlet = (e.get("source") or {}).get("title")
            if outlet:
                source = outlet
                title = re.sub(rf"\s+-\s+{re.escape(outlet)}$", "", title)
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
    new = [i for i in items if i["url"] not in known]
    if not new:
        return {"fetched": len(items), "new": 0, "feeds": len(feeds), "errors": errors,
                "seconds": round(time.perf_counter() - start, 1)}

    vectors = await embed_texts([f"{i['title']}. {i['summary']}" for i in new])
    topics = await tag_topics(vectors, [i["hints"] for i in new])

    clustered = 0
    with db() as conn:
        for item, vec, tags in zip(new, vectors, topics):
            row = conn.execute(
                """insert into articles (url, source, source_region, title, rss_summary, image_url,
                                         published_at, topics, embedding)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   on conflict (url) do nothing returning id""",
                (item["url"], item["source"], item["region"], item["title"], item["summary"],
                 item["image"], item["published"] or datetime.now(timezone.utc), tags, vec),
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
             "feeds": len(feeds), "errors": errors, "seconds": round(time.perf_counter() - start, 1)}
    log.info("ingest %s", stats)
    return stats
