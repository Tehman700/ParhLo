"""SWS on demand: fetch news for something a reader just followed, right away (not at the next 15-minute run).

  dashboard / search box: follow "Uganda" → POST /api/me/following/fetch
  → Google News search (+ Tavily when available) → store_items (gate keeps them: the reader asked) → reprint
Limits: INSTANT_PER_DAY per reader (follows + web answers together) and TAVILY_PER_MONTH overall (free tier is
1,000 credits). Over the Tavily budget it still works through Google News alone.
"""

from app.core.database import db
from app.core.errors import AppError
from app.parhlo import refresh
from app.parhlo.ingest import fetch_all, store_items
from app.parhlo.sws import gnews, tavily
from app.parhlo.sws.gate import make_gate

INSTANT_PER_DAY = 10
TAVILY_PER_MONTH = 900   # leave headroom under the 1,000 free credits
INSTANT_KEEP = 30        # stories stored per instant fetch (keeps it to a few seconds)


def quota(user: dict) -> tuple[bool, bool]:
    """(may search now, may use a Tavily credit)."""
    with db() as conn:
        today = conn.execute("select count(*) as n from sws_instant where user_id = %s "
                             "and created_at > now() - interval '1 day'", (user["id"],)).fetchone()["n"]
        month = conn.execute("select count(*) as n from sws_instant where tavily "
                             "and created_at > date_trunc('month', now())").fetchone()["n"]
    return today < INSTANT_PER_DAY, tavily.enabled() and month < TAVILY_PER_MONTH


def record(user: dict, kind: str, query: str, used_tavily: bool, found: int, added: int) -> None:
    with db() as conn:
        conn.execute("insert into sws_instant (user_id, kind, query, tavily, found, added) values (%s,%s,%s,%s,%s,%s)",
                     (user["id"], kind, query, used_tavily, found, added))


def check(user: dict) -> bool:
    """Raises when the reader hit today's limit; returns whether Tavily may be used."""
    allowed, use_tavily = quota(user)
    if not allowed:
        raise AppError("You've used today's instant searches. Your paper still picks this up at the next update.", 429)
    return use_tavily


async def fetch_interests(user: dict, limit: int = 5) -> dict:
    """News for what the reader follows and wrote in "About you", searched in parallel, stored once, one reprint.
    Each term counts toward the daily limit; terms over the limit wait for the regular runs."""
    import asyncio

    from app.parhlo.sws.planner import interest_phrases

    with db() as conn:
        prof = conn.execute("select entities from profiles where user_id = %s", (user["id"],)).fetchone() or {}
        phrases = list(interest_phrases(conn, user["id"]))
        today = conn.execute("select count(*) as n from sws_instant where user_id = %s "
                             "and created_at > now() - interval '1 day'", (user["id"],)).fetchone()["n"]
    terms = list(dict.fromkeys(t.strip() for t in [*(prof.get("entities") or []), *phrases] if t and t.strip()))
    terms = terms[:max(0, min(limit, INSTANT_PER_DAY - today))]
    if not terms:
        return {"terms": [], "found": 0, "added": 0}
    _, use_tavily = quota(user)
    feeds, _ = await fetch_all([gnews.search_feed(t) for t in terms])
    webs = await asyncio.gather(*(tavily.search(t) for t in terms)) if use_tavily else []
    found = [{**i, "requested": True} for i in feeds + [w for ws in webs for w in ws]]
    stats = await store_items(found, gate=make_gate(max_keep=INSTANT_KEEP * 2))
    stats.get("gate", {}).pop("_rejected", None)
    for t in terms:
        record(user, "follow", t, use_tavily, len(found), stats["kept"])
    await refresh.interests_changed(user, "news for " + ", ".join(terms))
    return {"terms": terms, "found": len(found), "added": stats["kept"], "web_search": use_tavily}


async def fetch_for(user: dict, name: str) -> dict:
    """News about `name` now: Google News search + Tavily, stored (gated as 'requested'), then a reprint."""
    name = " ".join(name.split())[:80]
    if not name:
        raise ValueError("Enter a name to search for")
    use_tavily = check(user)
    items, _ = await fetch_all([gnews.search_feed(name)])
    web = await tavily.search(name) if use_tavily else []
    found = [{**i, "requested": True} for i in items + web]
    stats = await store_items(found, gate=make_gate(max_keep=INSTANT_KEEP))
    stats.get("gate", {}).pop("_rejected", None)
    record(user, "follow", name, use_tavily, len(found), stats["kept"])
    await refresh.interests_changed(user, f"news for {name}")
    return {"query": name, "found": len(found), "added": stats["kept"], "already_had": len(found) - stats["new"],
            "web_search": use_tavily}
