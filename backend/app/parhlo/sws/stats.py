"""SWS at a glance (GET /api/admin/sws, behind the cron secret): is it running, what came in, what it costs."""

from app.core.database import db
from app.parhlo.sws.instant import TAVILY_PER_MONTH


def overview() -> dict:
    with db() as conn:
        runs = conn.execute(
            """select id, started_at, status, report->>'seconds' as seconds, report->>'new' as new,
                      report->>'kept' as kept, report->'gate' as gate, report->'searches' as searches, error
               from sws_runs order by started_at desc limit 10""").fetchall()
        last_done = conn.execute("select extract(epoch from now() - max(finished_at)) / 60 as mins "
                                 "from sws_runs where status = 'done'").fetchone()["mins"]
        day = "fetched_at > now() - interval '24 hours'"
        by_origin = conn.execute(f"select origin, count(*) as n from articles where {day} group by 1 order by 2 desc").fetchall()
        countries = conn.execute(f"select country, count(*) as n from articles where {day} and country is not null "
                                 "group by 1 order by 2 desc limit 15").fetchall()
        languages = conn.execute(f"select coalesce(language, 'en') as language, count(*) as n from articles where {day} "
                                 "group by 1 order by 2 desc limit 12").fetchall()
        sources = conn.execute(f"select source, count(*) as n from articles where {day} and origin <> 'rss' "
                               "group by 1 order by 2 desc limit 15").fetchall()
        planner = conn.execute("""select kind, count(*) as searches, count(*) filter (where next_run_at <= now()) as due,
                                         round(avg(interval_min)) as avg_interval_min
                                  from sws_queries group by 1 order by 1""").fetchall()
        busiest = conn.execute("select kind, query, hits, interval_min from sws_queries "
                               "order by hits desc, interval_min limit 8").fetchall()
        instant = conn.execute("""select count(*) filter (where created_at > now() - interval '24 hours') as today,
                                         count(*) filter (where tavily and created_at > date_trunc('month', now())) as tavily_month
                                  from sws_instant""").fetchone()
    return {
        "healthy": last_done is not None and last_done < 35,
        "minutes_since_last_run": round(last_done, 1) if last_done is not None else None,
        "last_24h": {"by_origin": {r["origin"]: r["n"] for r in by_origin},
                     "countries": {r["country"]: r["n"] for r in countries},
                     "languages": {r["language"]: r["n"] for r in languages},
                     "web_sources": {r["source"]: r["n"] for r in sources}},
        "planner": [dict(r) for r in planner],
        "busiest_searches": [dict(r) for r in busiest],
        "instant": {"searches_24h": instant["today"], "tavily_credits_this_month": instant["tavily_month"],
                    "tavily_budget": TAVILY_PER_MONTH},
        "runs": [{**dict(r), "started_at": r["started_at"].isoformat()} for r in runs],
    }
