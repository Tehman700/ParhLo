"""Reprint today's paper when the reader's interests change, orchestrated by an n8n workflow.

  dashboard change ──► interests_changed()  ── stamps users.interests_changed_at, POSTs a signed event to n8n
  n8n: Webhook ─► Wait 8 s (debounce) ─► POST /api/internal/paper/check ─► IF act ─► POST /api/internal/paper/refresh
  refresh ──► generate_edition(force) under the one-build-per-reader lock (new interests → new stories),
              notifies "paper updated"

The event carries an HMAC token over (user, change time), so n8n holds no secrets and nobody can forge a reprint.
Debounce: a check for an older change than the latest one stops ("newer change pending"); the newer event wins.
If n8n is unreachable, the paper page notices the paper is out of date and asks for the same refresh itself.
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

MIN_GAP_S = 60           # at most one reprint a minute per reader
MAX_PER_DAY = 15         # and a daily cap (each reprint costs a paper's worth of AI calls)


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
        today = conn.execute("select count(*) as n from notifications where user_id = %s and kind = 'paper_updated' "
                             "and created_at > now() - interval '1 day'", (u["id"],)).fetchone()["n"]
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
    if (datetime.now(timezone.utc) - ed["created_at"]).total_seconds() < MIN_GAP_S:
        return {**base, "act": False, "reason": "reprinted less than a minute ago"}
    if today >= MAX_PER_DAY:
        return {**base, "act": False, "reason": "daily reprint limit reached"}
    return {**base, "act": True, "reason": "out of date"}


def check(ev: RefreshEvent) -> dict:
    _verify(ev)
    d = decide(ev.user_id, ev.changed_ms)
    return {"act": d["act"], "reason": d["reason"]}


async def refresh(user_id: str, changed_ms: int | None) -> dict:
    d = decide(user_id, changed_ms)
    if not d["act"]:
        return {"status": "skipped", "reason": d["reason"]}
    user = d["user"]
    t0 = datetime.now(timezone.utc)
    ed = await editions.generate_edition(user, editions.today_pkt(), force=True)
    with db() as conn:
        friends.notify(conn, user["id"], "paper_updated", data={"date": ed["edition_date"]})
    return {"status": "refreshed", "stories": len(ed["stories"]),
            "seconds": round((datetime.now(timezone.utc) - t0).total_seconds(), 1)}


async def refresh_event(ev: RefreshEvent) -> dict:
    _verify(ev)
    return await refresh(ev.user_id, ev.changed_ms)


def status(user: dict) -> dict:
    """For the dashboard and paper page: is today's paper out of date, and is a reprint running?"""
    with db() as conn:
        ed = conn.execute("select created_at from editions where user_id = %s and edition_date = %s",
                          (user["id"], editions.today_pkt())).fetchone()
        building = bool(conn.execute("select 1 from edition_jobs where user_id = %s and edition_date = %s",
                                     (user["id"], editions.today_pkt())).fetchone())
        latest = conn.execute("select interests_changed_at from users where id = %s", (user["id"],)).fetchone()["interests_changed_at"]
    stale = bool(ed and latest and latest > ed["created_at"])
    return {"date": editions.today_pkt().isoformat(), "printed_at": ed["created_at"].isoformat() if ed else None,
            "interests_changed_at": latest.isoformat() if latest else None, "stale": stale, "building": building,
            "orchestrator": "n8n" if get_settings().n8n_webhook_url else None}
