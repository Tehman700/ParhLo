"""SWS query planner: what to search this run, and how often each search deserves to run.

Every search is a row in sws_queries with its own schedule:
  edition   top stories of an English Google News edition ("UG")           every 30 min – 4 h
  native    top stories of a native-language edition ("FR", in French)      every 1 – 6 h
  country   English news about a country without an edition ("Bangladesh")  every 2 – 12 h
  follow    a name readers follow ("Babar Azam"), more readers = higher priority   every 15 min – 4 h
  interest  a phrase from a reader's "About you" ("car accident news")          every 30 min – 6 h
  breaking  a story that just reached 3+ outlets: search for more coverage      every 30 min, for 6 h
Each run takes the due searches, highest priority first, up to a budget. After the run, a search that found
3+ new stories runs twice as often; one that found nothing waits twice as long (within its kind's bounds).
"""

import math
import re

from app.core.database import db
from app.parhlo.sws import gnews
from app.parhlo.topics import TOPICS

QUERIES_PER_RUN = 20
COUNTRY_SLOTS = 4      # of each run's budget, kept for countries without an English edition
# kind → (start interval, shortest, longest) in minutes, and base priority
SCHEDULE = {"follow": (30, 15, 240), "interest": (60, 30, 360), "edition": (60, 30, 240), "native": (120, 60, 360),
            "country": (240, 120, 720), "breaking": (30, 30, 60)}
PRIORITY = {"breaking": 2.0, "follow": 1.0, "interest": 0.9, "edition": 1.0, "native": 0.8, "country": 0.5}
BREAKING_MIN_OUTLETS = 3
BREAKING_HOURS = 6
STOP = {"with", "from", "that", "this", "after", "over", "into", "amid", "says", "will", "have", "been", "their",
        "about", "what", "when", "where", "which", "while", "more", "than", "they", "were", "could", "would"}


def interest_phrases(conn, user_id=None) -> dict[str, int]:
    """Phrases readers wrote in "About you" (stored as onboarding memories that aren't one of our 17 topics),
    with how many readers have each. user_id: just that reader's."""
    topic_labels = [t["label"].lower() for t in TOPICS.values()]
    rows = conn.execute(
        """select lower(label) as q, count(distinct user_id) as n from interest_anchors
           where kind = 'onboarding' and weight > 0 and not (lower(label) = any(%s))
             and (%s::uuid is null or user_id = %s::uuid)
           group by 1""", (topic_labels, user_id, user_id)).fetchall()
    return {r["q"]: r["n"] for r in rows if len(r["q"]) >= 3}


def adapt(kind: str, interval: int, new: int) -> int:
    """The next interval for a search that just found `new` new stories."""
    _, shortest, longest = SCHEDULE[kind]
    if new >= 3:
        return max(shortest, interval // 2)
    if new == 0:
        return min(longest, interval * 2)
    return interval


def keywords(title: str, n: int = 6) -> str:
    """A breaking headline → a short search ("Kenya confirms eighth Ebola case…" → "Kenya confirms eighth Ebola case")."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", title) if w.lower() not in STOP]
    return " ".join(list(dict.fromkeys(words))[:n])


def feed_for(row: dict) -> dict:
    """A sws_queries row → the Google News feed it reads (tagged with the query id for the hit count)."""
    kind, q = row["kind"], row["query"]
    feed = (gnews.edition_feed(q) if kind == "edition" else gnews.native_edition_feed(q) if kind == "native"
            else gnews.country_search_feed(q) if kind == "country" else gnews.search_feed(q))
    return {**feed, "query_id": row["id"]}


def sync() -> None:
    """Bring sws_queries up to date: every edition and country, every followed name, and breaking stories."""
    start = {k: v[0] for k, v in SCHEDULE.items()}
    with db() as conn:
        rows = [("edition", cc, PRIORITY["edition"], start["edition"]) for cc in gnews.EDITIONS]
        rows += [("native", cc, PRIORITY["native"], start["native"]) for cc in gnews.NATIVE_EDITIONS]
        rows += [("country", c, PRIORITY["country"], start["country"]) for c in gnews.COUNTRIES]
        follows = conn.execute("select e as name, count(*) as n from profiles, jsonb_array_elements_text(entities) e "
                               "group by e").fetchall()
        rows += [("follow", r["name"], PRIORITY["follow"] + 0.5 * math.log1p(r["n"]), start["follow"]) for r in follows]
        phrases = interest_phrases(conn)
        rows += [("interest", q, PRIORITY["interest"] + 0.5 * math.log1p(n), start["interest"]) for q, n in phrases.items()]
        breaking = conn.execute(
            """select (array_agg(title order by coalesce(importance, 0) desc))[1] as title
               from articles where fetched_at > now() - interval '3 hours' and cluster_id is not null
                 and coalesce(junk, 0) < 0.78
               group by cluster_id having count(distinct source) >= %s
               order by count(distinct source) desc limit 5""", (BREAKING_MIN_OUTLETS,)).fetchall()
        rows += [("breaking", kw, PRIORITY["breaking"], start["breaking"])
                 for kw in {keywords(r["title"]) for r in breaking} if len(kw.split()) >= 3]
        with conn.cursor() as cur:
            cur.executemany(  # new searches start due now; existing ones keep their schedule, priority updates
                """insert into sws_queries (kind, query, priority, interval_min) values (%s,%s,%s,%s)
                   on conflict (kind, query) do update set priority = excluded.priority""", rows)
        followed = [r["name"] for r in follows]
        conn.execute("delete from sws_queries where kind = 'follow' and not (query = any(%s))", (followed,))
        conn.execute("delete from sws_queries where kind = 'interest' and not (query = any(%s))", (list(phrases),))
        conn.execute("delete from sws_queries where kind = 'breaking' "
                     "and created_at < now() - make_interval(hours => %s)", (BREAKING_HOURS,))


def due(budget: int = QUERIES_PER_RUN, country_slots: int = COUNTRY_SLOTS) -> list[dict]:
    """The searches to run now, highest priority first — with a few slots kept for other countries, so busy
    follows and editions can't starve them (158 countries, 4 a run → each every few hours)."""
    with db() as conn:
        countries = conn.execute("select id, kind, query from sws_queries where kind = 'country' "
                                 "and next_run_at <= now() order by next_run_at limit %s", (country_slots,)).fetchall()
        rest = conn.execute("select id, kind, query from sws_queries where kind <> 'country' and next_run_at <= now() "
                            "order by priority desc, next_run_at limit %s", (budget - len(countries),)).fetchall()
        if len(countries) + len(rest) < budget:   # spare budget → more countries
            more = conn.execute("select id, kind, query from sws_queries where kind = 'country' and next_run_at <= now() "
                                "and not (id = any(%s)) order by next_run_at limit %s",
                                ([c["id"] for c in countries], budget - len(countries) - len(rest))).fetchall()
            countries += more
    return rest + countries


def record(rows: list[dict], new_by_query: dict[int, int]) -> None:
    """After a run: each search's new-story count decides when it runs next."""
    with db() as conn:
        for row in rows:
            new = new_by_query.get(row["id"], 0)
            cur = conn.execute("select interval_min from sws_queries where id = %s", (row["id"],)).fetchone()
            if not cur:
                continue
            nxt = adapt(row["kind"], cur["interval_min"], new)
            conn.execute(
                """update sws_queries set interval_min = %s, next_run_at = now() + make_interval(mins => %s),
                       last_run_at = now(), last_new = %s, hits = hits + (%s > 0)::int, misses = misses + (%s = 0)::int
                   where id = %s""", (nxt, nxt, new, new, new, row["id"]))
