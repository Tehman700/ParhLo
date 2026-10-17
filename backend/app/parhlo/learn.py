"""⑤ LEARN — events (short-term memory) → profile + interest anchors (long-term memory) → snapshot.

Signal values: like/save +1 · open +0.6 · dwell up to +0.4 · skip −0.3 · dislike −1 · quiz_correct +0.2
Immediate: like / save / dislike create an anchor from the article (so "more like this" works at once).
Consolidate (nightly cron or "update my paper"): topic weights, click anchors, source affinity, decay, snapshot.
"""

import math
from collections import defaultdict

from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from app.core.database import db
from app.parhlo.profile import add_anchors
from app.parhlo.topics import TOPICS

SIGNAL = {"like": 1.0, "save": 1.0, "open": 0.6, "skip": -0.3, "dislike": -1.0, "quiz_correct": 0.2}
EVENT_TYPES = {*SIGNAL, "dwell", "listen", "ask", "pdf", "quiz_wrong"}


class EventIn(BaseModel):
    type: str
    article_id: int | None = None
    edition_id: int | None = None
    value: float | None = Field(default=None, description="dwell seconds, etc.")


def signal(e: dict) -> float:
    if e["type"] == "dwell":
        return min(0.4, (e["value"] or 0) / 150)  # 60s ≈ +0.4
    return SIGNAL.get(e["type"], 0.0)


def record_events(user: dict, events: list[EventIn]) -> dict:
    events = [e for e in events if e.type in EVENT_TYPES]
    with db() as conn:
        for e in events:
            conn.execute("insert into events (user_id, edition_id, article_id, type, value) values (%s,%s,%s,%s,%s)",
                         (user["id"], e.edition_id, e.article_id, e.type, e.value))
        strong = [e for e in events if e.type in ("like", "save", "dislike") and e.article_id]
        if strong:
            arts = {a["id"]: a for a in conn.execute(
                "select id, title, embedding from articles where id = any(%s)", ([e.article_id for e in strong],))}
            rows = []
            for e in strong:
                a = arts.get(e.article_id)
                if a and a["embedding"] is not None:
                    w = -0.8 if e.type == "dislike" else 0.8
                    rows.append((a["title"], "disliked" if w < 0 else "liked", w, a["embedding"], a["id"]))
            add_anchors(conn, user["id"], rows)
    return {"recorded": len(events)}


def consolidate(user: dict) -> dict:
    """Fold recent events into the profile and write a snapshot explaining what changed."""
    with db() as conn:
        prof = conn.execute("select topics, source_affinity from profiles where user_id=%s", (user["id"],)).fetchone()
        if not prof:
            return {"changes": []}
        last = conn.execute("select max(taken_at) as t from profile_snapshots where user_id=%s",
                            (user["id"],)).fetchone()["t"]
        events = conn.execute(
            """select e.type, e.value, e.article_id, a.topics, a.source, a.title, a.embedding
               from events e left join articles a on a.id = e.article_id
               where e.user_id=%s and (%s::timestamptz is null or e.created_at > %s)""",
            (user["id"], last, last)).fetchall()

        topics = dict(prof["topics"] or {})
        affinity = dict(prof["source_affinity"] or {})
        before = dict(topics)
        per_topic: dict[str, list[float]] = defaultdict(list)
        per_source: dict[str, list[float]] = defaultdict(list)
        clicked: dict[int, dict] = {}
        for e in events:
            s = signal(e)
            for t in e["topics"] or []:
                per_topic[t].append(s)
            if e["source"]:
                per_source[e["source"]].append(s)
            if e["type"] in ("open", "dwell") and e["embedding"] is not None and s >= 0.3:
                clicked[e["article_id"]] = e

        for t in TOPICS:
            if t in per_topic:  # move toward engagement, bounded
                topics[t] = round(min(1.0, max(0.02, topics.get(t, 0.1) + 0.12 * math.tanh(sum(per_topic[t])))), 3)
            else:               # untouched interests fade slowly
                topics[t] = round(max(0.05, topics.get(t, 0.1) * 0.98), 3)
        for src, vals in per_source.items():
            affinity[src] = round(max(-0.5, min(0.5, 0.7 * affinity.get(src, 0) + 0.3 * (sum(vals) / len(vals)))), 3)

        add_anchors(conn, user["id"], [(e["title"], "clicked", 0.5, e["embedding"], aid) for aid, e in clicked.items()])
        conn.execute("update interest_anchors set weight = weight * 0.97 where user_id=%s and kind in "
                     "('clicked','liked','disliked')", (user["id"],))

        changes = []
        for t, new in topics.items():
            old = before.get(t, 0.1)
            if abs(new - old) >= 0.04 and t in per_topic:
                vals = per_topic[t]
                pos, neg = sum(1 for v in vals if v > 0), sum(1 for v in vals if v < 0)
                why = (f"You engaged with {pos} {TOPICS[t]['label']} stor{'y' if pos == 1 else 'ies'}" if new > old
                       else f"You skipped or disliked {neg} {TOPICS[t]['label']} stor{'y' if neg == 1 else 'ies'}")
                changes.append({"topic": t, "label": TOPICS[t]["label"], "from": old, "to": new, "why": why})
        changes.sort(key=lambda c: -abs(c["to"] - c["from"]))

        conn.execute("update profiles set topics=%s, source_affinity=%s, updated_at=now() where user_id=%s",
                     (Jsonb(topics), Jsonb(affinity), user["id"]))
        conn.execute("insert into profile_snapshots (user_id, topics, changes) values (%s,%s,%s)",
                     (user["id"], Jsonb(topics), Jsonb(changes)))
    return {"events": len(events), "changes": changes, "new_click_anchors": len(clicked)}
