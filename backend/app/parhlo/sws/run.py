"""One SWS run (every ~15 minutes, triggered by GitHub Actions → GET /api/cron/sws).

  1. claim the run (one at a time: a unique 'running' row in sws_runs)
  2. read sources: new GDELT 15-minute windows (at most 2) + a rotating slice of Google News feeds:
     English country editions, English searches for other countries, and names readers follow
  3. store_items(…, gate): skip known → embed → gate (keep what readers could get) → Jev → store → cluster
  4. record the report (what was read, kept, dropped and why) — /api/cron/sws returns it too
Rotation: run N reads slice N of each list, so every edition is read about hourly and every other country
every few hours, without any single run getting slow.
"""

import logging
import time

import httpx
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.core.database import db
from app.parhlo.ingest import UA, fetch_all, jev_backfill, store_items
from app.parhlo.sws import gdelt, gnews
from app.parhlo.sws.gate import make_gate

log = logging.getLogger("parhlo.sws")

EDITIONS_PER_RUN = 6      # 23 editions → each about every hour
COUNTRIES_PER_RUN = 8     # ~150 countries → each every ~5 hours
FOLLOWS_PER_RUN = 6       # names readers follow
GDELT_SLOTS_PER_RUN = 2
STALE_MIN = 10            # a 'running' run older than this is assumed dead


def _slice(items: list, run_no: int, per_run: int) -> list:
    """Run N's share of a list, wrapping around (the rotation)."""
    if not items:
        return []
    start = (run_no * per_run) % len(items)
    return (items + items)[start:start + min(per_run, len(items))]


def _claim() -> tuple[int | None, int, str | None]:
    """Start a run unless one is already running. Returns (run id or None, run number, last GDELT window)."""
    with db() as conn:
        conn.execute("update sws_runs set status = 'failed', error = 'timed out', finished_at = now() "
                     "where status = 'running' and started_at < now() - make_interval(mins => %s)", (STALE_MIN,))
        row = conn.execute("insert into sws_runs default values on conflict do nothing returning id").fetchone()
        if not row:
            return None, 0, None
        n = conn.execute("select count(*) as n from sws_runs where status = 'done'").fetchone()["n"]
        last = conn.execute("select max(s) as s from sws_runs, unnest(gdelt_slots) s where status = 'done'").fetchone()
    return row["id"], n, last["s"]


def _finish(run_id: int, status: str, slots: list[str], feeds: int, report: dict, error: str | None = None) -> None:
    with db() as conn:
        conn.execute("update sws_runs set status = %s, finished_at = now(), gdelt_slots = %s, feeds = %s, "
                     "report = %s, error = %s where id = %s", (status, slots, feeds, Jsonb(report), error, run_id))


def _drop_recently_rejected(items: list[dict]) -> list[dict]:
    with db() as conn:
        gone = {r["url"] for r in conn.execute(
            "select url from sws_rejected where url = any(%s) and rejected_at > now() - interval '3 days'",
            ([i["url"] for i in items],))}
    return [i for i in items if i["url"] not in gone]


def _remember_rejected(urls: list[str]) -> None:
    if not urls:
        return
    with db() as conn:
        conn.execute("insert into sws_rejected (url) select unnest(%s::text[]) "
                     "on conflict (url) do update set rejected_at = now()", (urls,))
        conn.execute("delete from sws_rejected where rejected_at < now() - interval '3 days'")


def plan_feeds(run_no: int, follows: list[str]) -> list[dict]:
    """This run's Google News feeds: a slice of editions, of other countries, and of followed names."""
    return ([gnews.edition_feed(cc) for cc in _slice(list(gnews.EDITIONS), run_no, EDITIONS_PER_RUN)]
            + [gnews.country_search_feed(c) for c in _slice(gnews.COUNTRIES, run_no, COUNTRIES_PER_RUN)]
            + [gnews.search_feed(name) for name in _slice(follows, run_no, FOLLOWS_PER_RUN)])


def _follows() -> list[str]:
    """Names readers follow, most-followed first (so the busiest interests come round first)."""
    with db() as conn:
        rows = conn.execute("select e as name, count(*) as n from profiles, jsonb_array_elements_text(entities) e "
                            "group by e order by n desc, e").fetchall()
    return [r["name"] for r in rows]


async def run_once() -> dict:
    if not get_settings().sws_enabled:
        return {"status": "disabled"}
    run_id, run_no, last_slot = _claim()
    if run_id is None:
        return {"status": "skipped", "reason": "another SWS run is in progress"}
    t0 = time.perf_counter()
    slots: list[str] = []
    feeds: list[dict] = []
    report: dict = {"run": run_no}
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers={"User-Agent": UA}) as client:
            g_items, slots = await gdelt.fetch_new(last_slot, GDELT_SLOTS_PER_RUN, client)
        feeds = plan_feeds(run_no, _follows())
        n_items, errors = await fetch_all(feeds)
        fetched = g_items + n_items
        items = _drop_recently_rejected(fetched)
        report["skipped_rejected"] = len(fetched) - len(items)
        report.update({"gdelt_items": len(g_items), "gnews_items": len(n_items), "feed_errors": len(errors),
                       "countries": sorted({f["country"] for f in feeds if f.get("country")})})
        stored = await store_items(items, gate=make_gate())
        _remember_rejected(stored.get("gate", {}).pop("_rejected", []))
        report.update(stored)
        report.update(await jev_backfill(hours=6, limit=100))
        report["seconds"] = round(time.perf_counter() - t0, 1)
        _finish(run_id, "done", slots, len(feeds), report)
        log.info("sws run %s", report)
        return {"status": "done", "gdelt_slots": slots, "feeds": len(feeds), **report}
    except Exception as e:
        log.exception("sws run failed")
        _finish(run_id, "failed", slots, len(feeds), report, error=f"{type(e).__name__}: {e}"[:500])
        raise
