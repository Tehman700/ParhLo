"""One SWS run (every ~15 minutes, triggered by GitHub Actions → GET /api/cron/sws).

  1. claim the run (one at a time: a unique 'running' row in sws_runs)
  2. read sources: new GDELT 15-minute windows (English: at most 2, translated: 1) + the Google News searches
     that are due
     (planner.py: editions, other countries, followed names, breaking stories — each on its own schedule)
  3. store_items(…, gate): skip known → embed → gate (keep what readers could get) → Jev → store → cluster
  4. tell the planner how many new stories each search found (busy searches run more often, quiet ones less)
  5. record the report (what was read, kept, dropped and why) — /api/cron/sws returns it too
"""

import logging
import time
from collections import Counter

import httpx
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.core.database import db
from app.parhlo.ingest import UA, fetch_all, jev_backfill, store_items
from app.parhlo.sws import gdelt, planner
from app.parhlo.sws.gate import make_gate

log = logging.getLogger("parhlo.sws")

GDELT_SLOTS_PER_RUN = 2
GDELT_TRANSLATED_PER_RUN = 1   # ~2,800 articles from 65 languages per window; one per run keeps up (4 a run-hour)
STALE_MIN = 10            # a 'running' run older than this is assumed dead


def _claim() -> tuple[int | None, int, str | None, str | None]:
    """Start a run unless one is already running.
    Returns (run id or None, run number, last English GDELT window, last translated window ('t'-prefixed))."""
    with db() as conn:
        conn.execute("update sws_runs set status = 'failed', error = 'timed out', finished_at = now() "
                     "where status = 'running' and started_at < now() - make_interval(mins => %s)", (STALE_MIN,))
        row = conn.execute("insert into sws_runs default values on conflict do nothing returning id").fetchone()
        if not row:
            return None, 0, None, None
        n = conn.execute("select count(*) as n from sws_runs where status = 'done'").fetchone()["n"]
        last = conn.execute("select max(s) filter (where s not like 't%%') as en, "
                            "max(substr(s, 2)) filter (where s like 't%%') as tr "
                            "from sws_runs, unnest(gdelt_slots) s where status = 'done'").fetchone()
    return row["id"], n, last["en"], last["tr"]


def _finish(run_id: int, status: str, slots: list[str], feeds: int, report: dict, error: str | None = None) -> None:
    with db() as conn:
        conn.execute("update sws_runs set status = %s, finished_at = now(), gdelt_slots = %s, feeds = %s, "
                     "report = %s, error = %s where id = %s", (status, slots, feeds, Jsonb(report), error, run_id))


def _drop_recently_rejected(items: list[dict]) -> list[dict]:
    """Skip stories the gate rejected in the last 3 days — unless a reader has changed interests since then
    (follows "Uganda" → yesterday's rejected Uganda stories get a fresh look)."""
    with db() as conn:
        gone = {r["url"] for r in conn.execute(
            """select url from sws_rejected where url = any(%s) and rejected_at > now() - interval '3 days'
                 and rejected_at > coalesce((select max(interests_changed_at) from users), '-infinity')""",
            ([i["url"] for i in items],))}
    return [i for i in items if i["url"] not in gone]


def _remember_rejected(urls: list[str]) -> None:
    if not urls:
        return
    with db() as conn:
        conn.execute("insert into sws_rejected (url) select unnest(%s::text[]) "
                     "on conflict (url) do update set rejected_at = now()", (urls,))
        conn.execute("delete from sws_rejected where rejected_at < now() - interval '3 days'")


def _new_counts(items: list[dict]) -> dict[int, int]:
    """Per planner search: how many of its items we had never seen (not stored, not rejected)."""
    with db() as conn:
        seen = {r["url"] for r in conn.execute(
            "select url from articles where url = any(%s) union select url from sws_rejected where url = any(%s)",
            ([i["url"] for i in items], [i["url"] for i in items]))}
    return dict(Counter(i["query_id"] for i in items if i.get("query_id") and i["url"] not in seen))


async def run_once() -> dict:
    if not get_settings().sws_enabled:
        return {"status": "disabled"}
    run_id, run_no, last_slot, last_translated = _claim()
    if run_id is None:
        return {"status": "skipped", "reason": "another SWS run is in progress"}
    t0 = time.perf_counter()
    slots: list[str] = []
    feeds: list[dict] = []
    report: dict = {"run": run_no}
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers={"User-Agent": UA}) as client:
            g_items, slots = await gdelt.fetch_new(last_slot, GDELT_SLOTS_PER_RUN, client)
            t_items, t_slots = await gdelt.fetch_new(last_translated, GDELT_TRANSLATED_PER_RUN, client, translated=True)
        slots += ["t" + s for s in t_slots]   # translated windows are stored 't'-prefixed in sws_runs
        g_items += t_items
        planner.sync()
        searches = planner.due()
        feeds = [planner.feed_for(r) for r in searches]
        n_items, errors = await fetch_all(feeds)
        new_by_query = _new_counts(n_items)
        fetched = g_items + n_items
        items = _drop_recently_rejected(fetched)
        report["skipped_rejected"] = len(fetched) - len(items)
        report.update({"gdelt_items": len(g_items), "gdelt_translated": len(t_items), "gnews_items": len(n_items),
                       "feed_errors": len(errors),
                       "searches": dict(Counter(r["kind"] for r in searches)),
                       "countries": sorted({f["country"] for f in feeds if f.get("country")})})
        stored = await store_items(items, gate=make_gate())
        _remember_rejected(stored.get("gate", {}).pop("_rejected", []))
        report.update(stored)
        planner.record(searches, new_by_query)
        report["searches_with_new"] = sum(1 for n in new_by_query.values() if n)
        report.update(await jev_backfill(hours=6, limit=100))
        report["seconds"] = round(time.perf_counter() - t0, 1)
        _finish(run_id, "done", slots, len(feeds), report)
        log.info("sws run %s", report)
        return {"status": "done", "gdelt_slots": slots, "feeds": len(feeds), **report}
    except Exception as e:
        log.exception("sws run failed")
        _finish(run_id, "failed", slots, len(feeds), report, error=f"{type(e).__name__}: {e}"[:500])
        raise
