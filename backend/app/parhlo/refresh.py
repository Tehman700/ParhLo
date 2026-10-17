"""Reprint today's paper the moment the reader's interests change, then polish it in the background.

  dashboard change ─► interests_changed(): stamps users.interests_changed_at, sends a signed event to n8n
  the page (≈1 s after the last change) ─► POST /api/editions/refresh: FAST reprint, no AI in the critical path
        (SQL ranking, stored summaries or excerpts, simple layout, cached morning box) → new paper in the response
  then ─► POST /api/editions/polish: AI summaries for excerpt-only stories + the AI editor, swapped in silently
  n8n (Webhook → Wait → check → IF → refresh): the guarantee when the page is closed; it reprints AND polishes.
        Its check says "already up to date" when the page got there first, so nothing runs twice.

Events carry an HMAC token over (user, change time): n8n holds no secrets and nobody can forge a reprint.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import db
from app.parhlo import editions, friends
from app.parhlo.auth import AuthError

log = logging.getLogger("parhlo.refresh")

MAX_PER_DAY = 100        # fast reprints use no AI; the cap only stops runaway loops


class RefreshEvent(BaseModel):
    user_id: str
    changed_ms: int
    token: str


def _token(user_id: str, changed_ms: int) -> str:
    key = (get_settings().session_secret or "dev").encode()
    return hmac.new(key, f"interests:{user_id}:{changed_ms}".encode(), hashlib.sha256).hexdigest()


def _ms(ts: datetime) -> int:
    return int(ts.timestamp() * 1000)


async def interests_changed(user: dict, what: str) -> dict:
    """Call after any change that affects story choice. Never fails the reader's request."""
    if user.get("persona") or not user.get("onboarded"):
        return {"queued": False}
    with db() as conn:
        ts = conn.execute("update users set interests_changed_at = now() where id = %s returning interests_changed_at",
                          (user["id"],)).fetchone()["interests_changed_at"]
    s = get_settings()
    if not s.n8n_webhook_url:
        return {"queued": False, "via": None}
    ms = _ms(ts)
    event = {"user_id": str(user["id"]), "changed_ms": ms, "token": _token(str(user["id"]), ms), "what": what,
             "callback": f"{s.public_url.rstrip('/')}/api/internal/paper"}
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.post(s.n8n_webhook_url, json=event)
        return {"queued": r.status_code < 300, "via": "n8n"}
    except httpx.HTTPError as e:  # n8n down: the paper page's stale check is the fallback
        log.warning("n8n webhook failed: %s", e)
        return {"queued": False, "via": None}


def _verify(ev: RefreshEvent) -> None:
    if not hmac.compare_digest(ev.token, _token(ev.user_id, ev.changed_ms)):
        raise AuthError("Bad refresh token")


def decide(user_id: str, changed_ms: int | None) -> dict:
    """Should today's paper be reprinted now? changed_ms=None means "for the latest change" (reader-initiated)."""
    with db() as conn:
        u = conn.execute("select * from users where id::text = %s", (user_id,)).fetchone()
        if not u:
            return {"act": False, "reason": "unknown reader"}
        ed = conn.execute("select created_at from editions where user_id = %s and edition_date = %s",
                          (u["id"], editions.today_pkt())).fetchone()
        building = conn.execute("select 1 from edition_jobs where user_id = %s and edition_date = %s",
                                (u["id"], editions.today_pkt())).fetchone()
        today = conn.execute("select coalesce((data->'reprints')::int, 0) as n from editions where user_id = %s "
                             "and edition_date = %s", (u["id"], editions.today_pkt())).fetchone()
        today = today["n"] if today else 0
    latest = u.get("interests_changed_at")
    base = {"user": u}
    if u.get("persona"):
        return {**base, "act": False, "reason": "sample reader"}
    if not latest:
        return {**base, "act": False, "reason": "no interest changes"}
    if changed_ms is not None and changed_ms < _ms(latest):
        return {**base, "act": False, "reason": "newer change pending"}
    if not ed:
        return {**base, "act": False, "reason": "no paper today yet (it will use the new interests)"}
    if ed["created_at"] >= latest:
        return {**base, "act": False, "reason": "paper already up to date"}
    if building:
        return {**base, "act": False, "reason": "already reprinting"}
    if today >= MAX_PER_DAY:
        return {**base, "act": False, "reason": "daily reprint limit reached"}
    return {**base, "act": True, "reason": "out of date", "reprints": today}


def check(ev: RefreshEvent) -> dict:
    _verify(ev)
    d = decide(ev.user_id, ev.changed_ms)
    return {"act": d["act"], "reason": d["reason"]}


async def refresh(user_id: str, changed_ms: int | None, polish: bool = False) -> dict:
    """Fast reprint if the paper is out of date. polish=True (n8n, page closed) also runs the AI polish."""
    d = decide(user_id, changed_ms)
    if not d["act"]:
        return {"status": "skipped", "reason": d["reason"]}
    user = d["user"]
    t0 = datetime.now(timezone.utc)
    ed = await editions.generate_edition(user, editions.today_pkt(), force=True, fast=True)
    with db() as conn:
        conn.execute("update editions set data = jsonb_set(data, '{reprints}', to_jsonb(%s::int)) where id = %s",
                     (int((d.get("reprints") or 0)) + 1, ed["id"]))
    out = {"status": "refreshed", "seconds": round((datetime.now(timezone.utc) - t0).total_seconds(), 2),
           "build_ms": ed.get("build_ms"), "edition": ed}
    if polish:
        polished = await editions.polish_edition(user, editions.today_pkt())
        with db() as conn:  # the reader wasn't watching: tell them
            friends.notify(conn, user["id"], "paper_updated", data={"date": ed["edition_date"]})
        out["polished"] = bool(polished)
    return out


async def refresh_event(ev: RefreshEvent) -> dict:
    _verify(ev)
    out = await refresh(ev.user_id, ev.changed_ms, polish=True)
    out.pop("edition", None)  # n8n doesn't need the paper itself
    return out


def status(user: dict) -> dict:
    """For the dashboard and paper page: is today's paper out of date, and is a reprint running?"""
    with db() as conn:
        ed = conn.execute("select created_at, data->>'phase' as phase, data->>'generated_at' as version "
                          "from editions where user_id = %s and edition_date = %s",
                          (user["id"], editions.today_pkt())).fetchone()
        building = bool(conn.execute("select 1 from edition_jobs where user_id = %s and edition_date = %s",
                                     (user["id"], editions.today_pkt())).fetchone())
        latest = conn.execute("select interests_changed_at from users where id = %s", (user["id"],)).fetchone()["interests_changed_at"]
    stale = bool(ed and latest and latest > ed["created_at"])
    phase = ed["phase"] if ed else None
    return {"date": editions.today_pkt().isoformat(), "printed_at": ed["created_at"].isoformat() if ed else None,
            "interests_changed_at": latest.isoformat() if latest else None, "stale": stale, "building": building,
            "phase": phase, "version": ed["version"] if ed else None,
            "orchestrator": "n8n" if get_settings().n8n_webhook_url else None}
