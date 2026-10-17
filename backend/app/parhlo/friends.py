"""Friends: invite links, notifications, and (when a reader turns it on) friends shaping each other's papers.

One switch per reader, `learn_from_friends`. A friend's likes and saves only reach your paper when you AND that
friend have it on. Two effects:
  - friend picks: up to 2 stories your friends liked recently, labelled "Ali liked this"
  - a gentle nightly drift of your topic weights toward your friends' strong interests
Turning the switch off stops both from then on; nothing already learned is undone.
"""

import secrets

from psycopg.types.json import Jsonb

from app.core.database import db
from app.core.errors import AppError, NotFoundError
from app.parhlo.topics import TOPICS

FRIEND_PICKS = 2
FRIEND_LIKE_DAYS = 3
BLEND_RATE = 0.1     # move 10% of the gap toward friends' interest per night...
BLEND_MAX = 0.03     # ...but never more than this per topic per night
FRIEND_STRONG = 0.5  # only friends' strong interests pull


def display_name(row: dict) -> str:
    name = (row.get("name") or "").strip()
    if name and name not in ("Reader", "Guest"):
        return name
    email = row.get("email") or ""
    return email.split("@")[0] if email else "A friend"


# ---------- notifications ----------

def notify(conn, user_id, kind: str, actor_id=None, data: dict | None = None) -> None:
    conn.execute("insert into notifications (user_id, kind, actor_id, data) values (%s,%s,%s,%s)",
                 (user_id, kind, actor_id, Jsonb(data or {})))


def list_notifications(user_id, limit: int = 20) -> dict:
    with db() as conn:
        rows = conn.execute(
            """select n.id, n.kind, n.data, n.read_at, n.created_at, u.name as actor_name, u.email as actor_email
               from notifications n left join users u on u.id = n.actor_id
               where n.user_id=%s order by n.created_at desc limit %s""", (user_id, limit)).fetchall()
        unread = conn.execute("select count(*) as n from notifications where user_id=%s and read_at is null",
                              (user_id,)).fetchone()["n"]
    items = [{"id": r["id"], "kind": r["kind"], "data": r["data"], "read": r["read_at"] is not None,
              "created_at": r["created_at"].isoformat(),
              "actor": display_name({"name": r["actor_name"], "email": r["actor_email"]}) if r["actor_name"] else None}
             for r in rows]
    return {"unread": unread, "items": items}


def mark_read(user_id) -> dict:
    with db() as conn:
        conn.execute("update notifications set read_at = now() where user_id=%s and read_at is null", (user_id,))
    return {"unread": 0}


# ---------- invites and friendships ----------

def invite_code(user: dict) -> str:
    with db() as conn:
        row = conn.execute("select invite_code from users where id=%s", (user["id"],)).fetchone()
        if row and row["invite_code"]:
            return row["invite_code"]
        code = secrets.token_urlsafe(6).replace("-", "x").replace("_", "y")
        conn.execute("update users set invite_code=%s where id=%s", (code, user["id"]))
    return code


def invite_info(code: str) -> dict:
    with db() as conn:
        row = conn.execute("select id, name, email from users where invite_code=%s", (code,)).fetchone()
    if not row:
        raise NotFoundError("This invite link isn't valid.")
    return {"inviter": display_name(row), "inviter_id": str(row["id"])}


def accept_invite(user: dict, code: str) -> dict:
    if user.get("is_demo"):
        raise AppError("Create an account to accept an invite.", 400)
    with db() as conn:
        inviter = conn.execute("select id, name, email from users where invite_code=%s", (code,)).fetchone()
        if not inviter:
            raise NotFoundError("This invite link isn't valid.")
        if inviter["id"] == user["id"]:
            raise AppError("That's your own invite link. Send it to a friend.", 400)
        added = conn.execute(
            """insert into friendships (user_id, friend_id) values (%s,%s), (%s,%s)
               on conflict do nothing returning user_id""",
            (user["id"], inviter["id"], inviter["id"], user["id"])).fetchall()
        if added:
            notify(conn, inviter["id"], "invite_accepted", user["id"])
            notify(conn, user["id"], "friend_added", inviter["id"])
    return {"friend": display_name(inviter), "already": not added}


def list_friends(user: dict) -> dict:
    with db() as conn:
        me = conn.execute("select learn_from_friends from users where id=%s", (user["id"],)).fetchone()
        rows = conn.execute(
            """select u.id, u.name, u.email, u.learn_from_friends, f.created_at
               from friendships f join users u on u.id = f.friend_id
               where f.user_id=%s order by f.created_at desc""", (user["id"],)).fetchall()
    return {
        "learn_from_friends": bool(me and me["learn_from_friends"]),
        "invite_code": invite_code(user),
        "friends": [{"id": str(r["id"]), "name": display_name(r), "since": r["created_at"].isoformat(),
                     "sharing": r["learn_from_friends"]} for r in rows],
    }


def remove_friend(user: dict, friend_id: str) -> dict:
    with db() as conn:
        conn.execute("delete from friendships where (user_id=%s and friend_id=%s) or (user_id=%s and friend_id=%s)",
                     (user["id"], friend_id, friend_id, user["id"]))
    return list_friends(user)


def _sharing_friends(conn, user_id) -> list[dict]:
    """Friends who also have learn_from_friends on (empty if the reader has it off)."""
    return conn.execute(
        """select u.id, u.name, u.email from friendships f
           join users u on u.id = f.friend_id
           join users me on me.id = f.user_id
           where f.user_id=%s and me.learn_from_friends and u.learn_from_friends""", (user_id,)).fetchall()


# ---------- effects on the paper ----------

def add_friend_picks(user: dict, pool: list[dict], picks: list[dict]) -> list[dict]:
    """Label chosen stories friends liked, and swap in up to FRIEND_PICKS of them for the weakest personal picks."""
    with db() as conn:
        friends = _sharing_friends(conn, user["id"])
        if not friends:
            return picks
        names = {f["id"]: display_name(f) for f in friends}
        liked = conn.execute(
            """select article_id, user_id, reaction, saved from article_state
               where user_id = any(%s) and (reaction = 'like' or saved)
                 and updated_at > now() - make_interval(days => %s)
               order by updated_at desc""", (list(names), FRIEND_LIKE_DAYS)).fetchall()
    if not liked:
        return picks
    by_article: dict[int, dict] = {}
    for r in liked:
        by_article.setdefault(r["article_id"], {"friend": names[r["user_id"]], "friend_saved": not r["reaction"]})

    picks = [{**p, **by_article[p["id"]]} if p["id"] in by_article else p for p in picks]
    labelled = sum(1 for p in picks if p.get("friend"))
    chosen = {p["id"] for p in picks}
    extra = [{**p, **by_article[p["id"]]} for p in pool if p["id"] in by_article and p["id"] not in chosen]
    extra = extra[: max(0, FRIEND_PICKS - labelled)]
    if not extra:
        return picks
    # Replace the weakest personal (not core, not discovery, not friend) picks.
    replaceable = sorted((p for p in picks if not (p.get("core") or p.get("discovery") or p.get("friend"))),
                         key=lambda p: p["score"])[: len(extra)]
    drop = {p["id"] for p in replaceable}
    return [p for p in picks if p["id"] not in drop] + extra[: len(drop)]


def blend_topics(conn, user: dict, topics: dict) -> list[dict]:
    """Nightly: drift (in place) toward friends' strong interests. Returns snapshot-style changes."""
    friends = _sharing_friends(conn, user["id"])
    if not friends:
        return []
    profs = conn.execute("select topics from profiles where user_id = any(%s)", ([f["id"] for f in friends],)).fetchall()
    if not profs:
        return []
    changes = []
    for t in TOPICS:
        own = topics.get(t, 0.1)
        if own <= 0.05:  # switched off (or fully faded): respect it
            continue
        avg = sum((p["topics"] or {}).get(t, 0.0) for p in profs) / len(profs)
        if avg >= FRIEND_STRONG and avg > own:
            delta = min(BLEND_MAX, BLEND_RATE * (avg - own))
            if delta >= 0.005:
                topics[t] = round(own + delta, 3)
                changes.append({"topic": t, "label": TOPICS[t]["label"], "from": own, "to": topics[t],
                                "why": f"Your friends read a lot about {TOPICS[t]['label']}", "friends": True})
    return changes
