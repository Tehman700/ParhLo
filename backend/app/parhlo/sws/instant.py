"""SWS on demand: when a reader changes their interests, search the web for them right away.

  follow a name / save "About you" / finish onboarding
  → for each term: Tavily advanced news search, in the reader's own words ("I want news related to Uganda Politics"),
    with the full article text and images in the same call (Extract fills in any result that came without text)
    + a Google News search for the same term (decoded to the publisher, image and text from the page)
  → richer summaries by gpt-5-mini from the full text (no Jev in this flow, by design)
  → store (the gate keeps them: the reader asked) → link each story to its term → reprint
Tavily runs only here and in Ask ("Search the web"), never in the hourly background runs. Limits: INSTANT_PER_DAY
searches per reader, TAVILY_PER_MONTH credits overall (free tier: 1,000; an advanced search costs 2).
"""

import asyncio
from datetime import datetime, timezone

from app.core.database import db
from app.core.errors import AppError
from app.parhlo import refresh
from app.parhlo.ingest import fetch_all, store_items
from app.parhlo.sws import enrich as enrich_mod
from app.parhlo.sws import gnews, tavily
from app.parhlo.sws.enrich import enrich
from app.parhlo.sws.gate import make_gate
from app.parhlo.sws.write import write_rich

INSTANT_PER_DAY = 30     # searches per reader per day (the monthly Tavily credit cap is the real cost guard)
TAVILY_PER_MONTH = 900   # credits; leave headroom under the 1,000 free
INSTANT_KEEP = 30        # stories stored per term at most
GNEWS_PER_TERM = 5       # newest Google News results per term (Tavily gives up to 8 more)
EXTRACT_MAX = 15         # pages still missing an image/text → Tavily Extract (1 credit per 5)
_OLD = datetime(1970, 1, 1, tzinfo=timezone.utc)


def quota(user: dict, credits_needed: int = 0) -> tuple[bool, bool]:
    """(may search now, may spend Tavily credits)."""
    with db() as conn:
        today = conn.execute("select count(*) as n from sws_instant where user_id = %s "
                             "and created_at > now() - interval '1 day'", (user["id"],)).fetchone()["n"]
        month = conn.execute("select coalesce(sum(credits), 0) as n from sws_instant "
                             "where created_at > date_trunc('month', now())").fetchone()["n"]
    return today < INSTANT_PER_DAY, tavily.enabled() and month + credits_needed <= TAVILY_PER_MONTH


def record(user: dict, kind: str, query: str, credits: int, found: int, added: int) -> None:
    with db() as conn:
        conn.execute("insert into sws_instant (user_id, kind, query, tavily, credits, found, added) "
                     "values (%s,%s,%s,%s,%s,%s,%s)", (user["id"], kind, query, credits > 0, credits, found, added))


def check(user: dict) -> bool:
    """Raises when the reader hit today's limit; returns whether Tavily may be used."""
    allowed, use_tavily = quota(user, 1)
    if not allowed:
        raise AppError("You've used today's instant searches. Your paper still picks this up at the next update.", 429)
    return use_tavily


async def gather_news(terms: list[str], use_tavily: bool) -> tuple[list[dict], int, dict]:
    """Web news for each term → items with link, image, full text and a rich summary where possible."""
    feeds, _ = await fetch_all([{**gnews.search_feed(t), "term": t} for t in terms])
    g_items = [i for t in terms
               for i in sorted((x for x in feeds if x.get("term") == t), key=lambda x: x["published"] or _OLD,
                               reverse=True)[:GNEWS_PER_TERM]]
    web: list[dict] = []
    credits = 0
    if use_tavily:
        for items, c in await asyncio.gather(*(tavily.search_news(t) for t in terms)):
            web += items
            credits += c
        missing = [i["url"] for i in web if not i.get("content")]
        if missing:   # a result without text: Tavily Extract (1 credit per 5 links)
            got, c = await tavily.extract(missing)
            credits += c
            for i in web:
                g = got.get(i["url"]) or {}
                i["content"] = i.get("content") or g.get("content")
                i["image"] = i.get("image") or g.get("image")
    filled = await enrich(g_items + [i for i in web if not i.get("image") or not i.get("content")])
    # Pages that refuse our servers (many publishers block cloud IPs): Tavily Extract reads them instead.
    still = [i for i in g_items + web if (i.get("link") or not enrich_mod.gn_id(i["url"]))
             and (not i.get("image") or not i.get("content"))][:EXTRACT_MAX]
    if use_tavily and still:
        got, c = await tavily.extract([i.get("link") or i["url"] for i in still])
        credits += c
        for i in still:
            g = got.get(i.get("link") or i["url"]) or {}
            i["content"] = i.get("content") or g.get("content")
            i["image"] = i.get("image") or g.get("image")
        filled["extract"] = sum(1 for i in still if i.get("content") or i.get("image"))
    items = [{**i, "requested": True} for i in g_items + web]
    written = await write_rich(items)
    return items, credits, {"web_results": len(web), "google_news": len(g_items), "enrich": filled,
                            "rich_summaries": written, "tavily_credits": credits}


async def _search(user: dict, terms: list[str], use_tavily: bool) -> dict:
    items, credits, report = await gather_news(terms, use_tavily)
    stats = await store_items(items, gate=make_gate(max_keep=INSTANT_KEEP * len(terms)), use_jev=False)
    _fill_known(items)
    stats.get("gate", {}).pop("_rejected", None)
    for n, t in enumerate(terms):
        record(user, "follow", t, credits if n == 0 else 0, len(items), stats["kept"])
    await refresh.interests_changed(user, "news for " + ", ".join(terms))
    return {"found": len(items), "added": stats["kept"], "already_had": len(items) - stats["new"],
            "web_search": use_tavily and report["web_results"] > 0, **report}


def _fill_known(items: list[dict]) -> None:
    """Stories we already had: keep what this search just found for them (publisher link, image, text, summary)."""
    from psycopg.types.json import Jsonb
    with db() as conn:
        for i in items:
            if i.get("image") or i.get("link") or i.get("ai_summary"):
                conn.execute(
                    """update articles set link = coalesce(link, %s), image_url = coalesce(image_url, %s),
                           content = coalesce(content, %s), ai_summary = coalesce(ai_summary, %s),
                           ai_points = case when ai_summary is null then coalesce(%s, ai_points) else ai_points end,
                           enriched_at = coalesce(enriched_at, now())
                       where url = %s""",
                    (i.get("link"), i.get("image"), i.get("content"), i.get("ai_summary"),
                     Jsonb(i["ai_points"]) if i.get("ai_points") else None, i["url"]))


async def fetch_interests(user: dict, limit: int = 5) -> dict:
    """Web news for what the reader follows and wrote in "About you" (after onboarding / saving "About you")."""
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
    _, use_tavily = quota(user, tavily.ADVANCED_CREDITS * len(terms))
    return {"terms": terms, **await _search(user, terms, use_tavily)}


async def fetch_for(user: dict, name: str) -> dict:
    """Web news about a name the reader just followed."""
    name = " ".join(name.split())[:80]
    if not name:
        raise ValueError("Enter a name to search for")
    check(user)
    _, use_tavily = quota(user, tavily.ADVANCED_CREDITS)
    return {"query": name, **await _search(user, [name], use_tavily)}
