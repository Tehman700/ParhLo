"""SWS source: Tavily web search — on demand, when a reader needs news we don't have yet.

Used sparingly (1,000 free credits a month; one basic search = 1 credit): a reader follows something new, or Ask
needs news that isn't in today's paper. Returns items in the parse_feed() shape (origin="web").
"""

import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx

from app.core.config import get_settings
from app.parhlo.ingest import MAX_AGE, clean_text
from app.parhlo.sws.outlets import outlet_name

log = logging.getLogger("parhlo.sws.tavily")

URL = "https://api.tavily.com/search"
TIMEOUT = 15.0


def enabled() -> bool:
    return bool(get_settings().tavily_api_key)


def _published(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)            # "Sun, 18 Oct 2026 07:05:00 GMT"
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def to_items(data: dict, max_age: timedelta = MAX_AGE) -> list[dict]:
    """Tavily's JSON → items. News older than max_age is dropped (48 hours by default, same rule as RSS)."""
    cutoff = datetime.now(timezone.utc) - max_age
    items = []
    for r in data.get("results") or []:
        url, title = r.get("url") or "", clean_text(r.get("title"), 300)
        if not url.startswith("http") or not title:
            continue
        published = _published(r.get("published_date"))
        if published and published < cutoff:
            continue
        items.append({
            "url": url, "title": title, "source": outlet_name(url), "region": "global",
            "summary": clean_text(r.get("content")), "image": None, "published": published,
            "hints": [], "origin": "web", "country": None, "language": "en",
        })
    return items


async def search(query: str, max_results: int = 8, days: int = 2, client: httpx.AsyncClient | None = None
                 ) -> list[dict]:
    """News search for `query` (last `days`). Returns [] when Tavily is off or fails — callers carry on."""
    if not enabled():
        return []
    body = {"query": query, "topic": "news", "days": days, "max_results": max_results, "search_depth": "basic"}
    headers = {"Authorization": f"Bearer {get_settings().tavily_api_key}"}
    own = client is None
    client = client or httpx.AsyncClient(timeout=TIMEOUT)
    try:
        r = await client.post(URL, json=body, headers=headers)
        if r.status_code != 200:
            log.warning("tavily HTTP %s: %s", r.status_code, r.text[:200])
            return []
        return to_items(r.json(), max(MAX_AGE, timedelta(days=days)))
    except httpx.HTTPError as e:
        log.warning("tavily unreachable: %s", e)
        return []
    finally:
        if own:
            await client.aclose()


# ---------- interest-change web search (advanced: full text + images in one call) ----------

EXTRACT_URL = "https://api.tavily.com/extract"
NEWS_QUERY = "I want news related to {term}"   # the reader's own words become the query
ADVANCED_CREDITS = 2
MIN_RAW = 400


def news_items(data: dict, term: str) -> list[dict]:
    """Advanced search JSON → items with the full text (raw_content) and the result's own image."""
    items = []
    by_url = {r.get("url"): r for r in data.get("results") or []}
    for item in to_items({"results": data.get("results") or []}, timedelta(days=7)):
        r = by_url.get(item["url"], {})
        raw = (r.get("raw_content") or "").strip()
        images = [i if isinstance(i, str) else (i or {}).get("url") for i in (r.get("images") or [])]
        items.append({**item, "term": term, "link": item["url"],
                      "content": raw[:20000] if len(raw) >= MIN_RAW else None,
                      "image": next((i for i in images if i and i.startswith("http")), None)})
    return items


async def search_news(term: str, max_results: int = 8, client: httpx.AsyncClient | None = None
                      ) -> tuple[list[dict], int]:
    """News about `term` from the last week, with full text and images. Returns (items, credits used)."""
    if not enabled():
        return [], 0
    body = {"query": NEWS_QUERY.format(term=term), "topic": "news", "search_depth": "advanced",
            "time_range": "week", "max_results": max_results, "include_raw_content": "text",
            "include_images": True, "include_published_date": True}
    data = await _post(URL, body, client)
    return (news_items(data, term), ADVANCED_CREDITS) if data is not None else ([], ADVANCED_CREDITS)


async def extract(urls: list[str], client: httpx.AsyncClient | None = None) -> tuple[dict[str, dict], int]:
    """Full text + images for known article URLs (fallback when a search result came without text).
    Returns ({url: {"content", "image"}}, credits used: 1 per 5 URLs)."""
    urls = urls[:20]
    if not enabled() or not urls:
        return {}, 0
    data = await _post(EXTRACT_URL, {"urls": urls, "include_images": True, "extract_depth": "basic",
                                     "format": "text"}, client)
    out = {}
    for r in (data or {}).get("results") or []:
        raw = (r.get("raw_content") or "").strip()
        imgs = [i for i in (r.get("images") or []) if isinstance(i, str) and i.startswith("http")]
        out[r.get("url")] = {"content": raw[:20000] if len(raw) >= MIN_RAW else None, "image": imgs[0] if imgs else None}
    return out, -(-len(urls) // 5)


async def _post(url: str, body: dict, client: httpx.AsyncClient | None) -> dict | None:
    own = client is None
    client = client or httpx.AsyncClient(timeout=40)
    try:
        r = await client.post(url, json=body, headers={"Authorization": f"Bearer {get_settings().tavily_api_key}"})
        if r.status_code != 200:
            log.warning("tavily %s HTTP %s: %s", url.rsplit("/", 1)[1], r.status_code, r.text[:200])
            return None
        return r.json()
    except httpx.HTTPError as e:
        log.warning("tavily unreachable: %s", e)
        return None
    finally:
        if own:
            await client.aclose()
