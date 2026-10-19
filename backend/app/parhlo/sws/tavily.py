"""SWS source: Tavily web search — on demand, when a reader needs news we don't have yet.

Used sparingly (1,000 free credits a month; one basic search = 1 credit): a reader follows something new, or Ask
needs news that isn't in today's paper. Returns items in the parse_feed() shape (origin="web").
"""

import logging
from datetime import datetime, timezone
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


def to_items(data: dict) -> list[dict]:
    """Tavily's JSON → items. News older than 48 hours is dropped (same rule as RSS)."""
    cutoff = datetime.now(timezone.utc) - MAX_AGE
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
        return to_items(r.json())
    except httpx.HTTPError as e:
        log.warning("tavily unreachable: %s", e)
        return []
    finally:
        if own:
            await client.aclose()
