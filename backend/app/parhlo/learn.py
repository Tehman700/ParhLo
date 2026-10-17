"""⑤ LEARN — events (short-term memory) → profile + interest anchors (long-term memory) → snapshot.

Signal values: like/save +1 · open +0.6 · ask +0.5 · dwell up to +0.4 · skip −0.3 · dislike −1 · quiz_correct +0.2
Immediate: like / save / dislike set the story's state (article_state) and its memory anchor, so "more like this"
works at once; unreact / unsave undo them. Only the current state counts when consolidating.
Consolidate (nightly cron or "update my paper"): topic weights, click anchors, source affinity, decay, snapshot.
"""

import math
from collections import defaultdict

from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from app.core.database import db
from app.parhlo import friends
from app.parhlo.profile import add_anchors
from app.parhlo.topics import TOPICS

SIGNAL = {"like": 1.0, "save": 1.0, "open": 0.6, "ask": 0.5, "skip": -0.3, "dislike": -1.0, "quiz_correct": 0.2}
MARKS = {"like", "dislike", "unreact", "save", "unsave"}
EVENT_TYPES = {*SIGNAL, *MARKS, "dwell", "listen", "ask", "pdf", "quiz_wrong"}
ONBOARDING_DECAY = 0.988  # per nightly consolidation → half-life ≈ 57 days
ONBOARDING_FLOOR = 0.3


class EventIn(BaseModel):
    type: str
    article_id: int | None = None
    edition_id: int | None = None
    value: float | None = Field(default=None, description="dwell seconds, etc.")


def signal(e: dict) -> float:
    # A like/dislike/save that was undone later no longer counts (events from before article_state count as-is).
    if e.get("has_state"):
        if e["type"] in ("like", "dislike") and e["cur_reaction"] != e["type"]:
            return 0.0
        if e["type"] == "save" and not e["cur_saved"]:
            return 0.0
    if e["type"] == "dwell":
        return min(0.4, (e["value"] or 0) / 150)  # 60s ≈ +0.4
    return SIGNAL.get(e["type"], 0.0)


def record_events(user: dict, events: list[EventIn]) -> dict:
    events = [e for e in events if e.type in EVENT_TYPES]
    with db() as conn:
        for e in events:
            conn.execute("insert into events (user_id, edition_id, article_id, type, value) values (%s,%s,%s,%s,%s)",
                         (user["id"], e.edition_id, e.article_id, e.type, e.value))
        marks = [e for e in events if e.type in MARKS and e.article_id]
        if marks:
            arts = {a["id"]: a for a in conn.execute(
                "select id, title, embedding from articles where id = any(%s)", ([e.article_id for e in marks],))}
            for e in marks:
                if e.article_id in arts:
                    _apply_mark(conn, user["id"], e.type, arts[e.article_id])
    return {"recorded": len(events)}


def _apply_mark(conn, user_id, kind: str, art: dict) -> None:
    st = conn.execute("select reaction, saved from article_state where user_id=%s and article_id=%s",
                      (user_id, art["id"])).fetchone() or {"reaction": None, "saved": False}
    reaction, saved = st["reaction"], st["saved"]
    if kind in ("like", "dislike"):
        reaction = kind
    elif kind == "unreact":
        reaction = None
    else:
        saved = kind == "save"
    conn.execute(
        """insert into article_state (user_id, article_id, reaction, saved) values (%s,%s,%s,%s)
           on conflict (user_id, article_id) do update set reaction = excluded.reaction, saved = excluded.saved,
               updated_at = now()""", (user_id, art["id"], reaction, saved))
    # One memory anchor per story, matching its current state.
    conn.execute("delete from interest_anchors where user_id=%s and article_id=%s and kind in ('liked','disliked')",
                 (user_id, art["id"]))
    w = -0.8 if reaction == "dislike" else 0.8 if (reaction == "like" or saved) else 0.0
    if w and art["embedding"] is not None:
        add_anchors(conn, user_id, [(art["title"], "liked" if w > 0 else "disliked", w, art["embedding"], art["id"])])


def reader_state(user_id, article_ids: list[int]) -> dict:
    """The reader's current reactions and saves for these stories (so the paper shows them after a reload)."""
    if not article_ids:
        return {"reactions": {}, "saved": []}
    with db() as conn:
        rows = conn.execute("select article_id, reaction, saved from article_state where user_id=%s "
                            "and article_id = any(%s)", (user_id, article_ids)).fetchall()
    return {"reactions": {str(r["article_id"]): r["reaction"] for r in rows if r["reaction"]},
            "saved": [r["article_id"] for r in rows if r["saved"]]}


def saved_stories(user_id, limit: int = 50) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """select a.id, a.title, a.source, a.url, a.image_url, a.ai_summary as summary, a.topics,
                      a.published_at, s.updated_at as saved_at
               from article_state s join articles a on a.id = s.article_id
               where s.user_id=%s and s.saved order by s.updated_at desc limit %s""", (user_id, limit)).fetchall()
    return [{**r, "published_at": r["published_at"].isoformat() if r["published_at"] else None,
             "saved_at": r["saved_at"].isoformat()} for r in rows]


def consolidate(user: dict) -> dict:
    """Fold recent events into the profile and write a snapshot explaining what changed."""
    with db() as conn:
        prof = conn.execute("select topics, source_affinity from profiles where user_id=%s", (user["id"],)).fetchone()
        if not prof:
            return {"changes": []}
        last = conn.execute("select max(taken_at) as t from profile_snapshots where user_id=%s",
                            (user["id"],)).fetchone()["t"]
        events = conn.execute(
            """select e.type, e.value, e.article_id, a.topics, a.source, a.title, a.embedding,
                      st.reaction as cur_reaction, coalesce(st.saved, false) as cur_saved,
                      (st.user_id is not null) as has_state
               from events e left join articles a on a.id = e.article_id
               left join article_state st on st.user_id = e.user_id and st.article_id = e.article_id
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
        friend_changes = friends.blend_topics(conn, user, topics)
        for src, vals in per_source.items():
            affinity[src] = round(max(-0.5, min(0.5, 0.7 * affinity.get(src, 0) + 0.3 * (sum(vals) / len(vals)))), 3)

        add_anchors(conn, user["id"], [(e["title"], "clicked", 0.5, e["embedding"], aid) for aid, e in clicked.items()])
        # Onboarding picks matter early, then fade slowly (half-life ~2 months) so real reading takes over,
        # like Spotify's onboarding signals. A floor keeps stated interests from vanishing entirely.
        conn.execute("update interest_anchors set weight = greatest(%s, weight * %s) where user_id=%s "
                     "and kind in ('onboarding','entity') and weight > %s",
                     (ONBOARDING_FLOOR, ONBOARDING_DECAY, user["id"], ONBOARDING_FLOOR))
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
        changes += [c for c in friend_changes if c["topic"] not in {x["topic"] for x in changes}]
        changes.sort(key=lambda c: -abs(c["to"] - c["from"]))

        conn.execute("update profiles set topics=%s, source_affinity=%s, updated_at=now() where user_id=%s",
                     (Jsonb(topics), Jsonb(affinity), user["id"]))
        conn.execute("insert into profile_snapshots (user_id, topics, changes) values (%s,%s,%s)",
                     (user["id"], Jsonb(topics), Jsonb(changes)))
    return {"events": len(events), "changes": changes, "new_click_anchors": len(clicked)}
