"""Morning email: each reader's paper, in their inbox.

A small job queue in Postgres (the "outbox" pattern), because Vercel functions can't run a Celery worker:
  enqueue  — the nightly print adds one job per reader and paper (a unique index makes it idempotent)
  drain    — a worker claims due jobs with FOR UPDATE SKIP LOCKED (two runs never take the same job),
             sends with bounded concurrency, retries failures with backoff, and records sent / failed.
             It runs right after the nightly print and again on its own cron (retries, stragglers).
One-click unsubscribe (RFC 8058) uses an HMAC token, so the link needs no sign-in.
The paper's PDF is attached (made once per paper and kept in S3, see pdfstore.py); the email also has a signed
PDF link (HMAC over reader + day + expiry) that opens without signing in, for any device.
"""

import asyncio
import hashlib
import hmac
import html
import logging
import time
from datetime import date, datetime

from app.core.config import get_settings
from app.core.database import db
from app.core.errors import AppError
from app.parhlo.mailer import send_email
from app.parhlo.topics import TOPICS

log = logging.getLogger("parhlo.digest")

MAX_ATTEMPTS = 3
CONCURRENCY = 4          # parallel SMTP sends per worker run
STALE_MIN = 10           # a "sending" job older than this is assumed lost and re-queued
MANUAL_PER_HOUR = 3      # "send me today's email" rate limit
DRAIN_BUDGET_S = 200     # stop claiming new jobs after this (PDFs take ~8 s; functions stop at 300 s)
PDF_TIMEOUT_S = 70       # making one PDF; past this the email goes with the link only


# ---------- unsubscribe token ----------

def unsubscribe_token(user_id) -> str:
    key = (get_settings().session_secret or "dev").encode()
    return hmac.new(key, f"unsubscribe:{user_id}".encode(), hashlib.sha256).hexdigest()[:32]


def unsubscribe_url(user_id) -> str:
    return f"{get_settings().public_url.rstrip('/')}/api/email/unsubscribe?u={user_id}&t={unsubscribe_token(user_id)}"


def unsubscribe(user_id: str, token: str) -> bool:
    if not hmac.compare_digest(token or "", unsubscribe_token(user_id)):
        return False
    with db() as conn:
        conn.execute("update users set email_morning = false where id::text = %s", (user_id,))
    return True


# ---------- signed PDF link (no sign-in; one reader, one day, read-only) ----------

PDF_LINK_DAYS = 30


def pdf_token(user_id, day: str, exp: int) -> str:
    key = (get_settings().session_secret or "dev").encode()
    return hmac.new(key, f"pdf:{user_id}:{day}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def pdf_query(user_id, day: str) -> str:
    exp = int(time.time()) + PDF_LINK_DAYS * 86400
    return f"u={user_id}&e={exp}&t={pdf_token(user_id, day, exp)}"


def verify_pdf(user_id: str, day: str, exp: int, token: str) -> bool:
    return exp >= time.time() and hmac.compare_digest(token or "", pdf_token(user_id, day, exp))


# ---------- rendering ----------

def _e(s) -> str:
    return html.escape(str(s or ""), quote=True)


def _topic(s: dict) -> str:
    return TOPICS.get((s.get("topics") or [""])[0], {}).get("label", "News")


def render(user: dict, paper: dict, edition_date: date, attached: bool = False) -> tuple[str, str, str]:
    """Subject, HTML and plain text for one reader's paper. Table layout and inline styles for email clients.
    attached: the PDF is attached to this email (the link stays as a second way to get it)."""
    base = get_settings().public_url.rstrip("/")
    day = edition_date.isoformat()
    paper_url, pdf_url = f"{base}/paper/{day}", f"{base}/pdf/{day}?{pdf_query(user['id'], day)}"
    pdf_label = "Your newspaper PDF is attached · Download it here" if attached else "Download the PDF"
    stories = paper.get("stories") or []
    lead = next((s for s in stories if s["id"] == paper.get("lead_id")), stories[0] if stories else None)
    rest = [s for s in stories if lead and s["id"] != lead["id"]][:6]
    when = edition_date.strftime("%A, %d %B %Y").replace(" 0", " ")
    reader = paper.get("reader") or {}
    subject = f"Your paper: {lead['headline']}" if lead else f"Your ParhLo paper for {when}"

    m = paper.get("morning") or {}
    w, a, r = m.get("weather"), m.get("air"), m.get("rates")
    morning = " · ".join(x for x in [
        f"{w['temp']}° {w['condition']} in {m.get('city', '')}" if w else "",
        f"Air quality {a['aqi']} ({a['label']})" if a and a.get("aqi") is not None else "",
        f"$1 = Rs {r['pkr']['USD']:.0f}" if r and r.get("pkr") else ""] if x)

    font = "-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Helvetica,Arial,sans-serif"
    serif = "Georgia,'Times New Roman',serif"

    def story_row(s: dict) -> str:
        badge = ("Top story" if s.get("core") else "New for you" if s.get("discovery") else
                 f"From {s['friend']}" if s.get("friend") else "")
        return f"""
<tr><td style="padding:18px 0;border-top:1px solid #e0e0e0">
  <div style="font-size:12px;font-weight:600;color:#0066cc">{_e(_topic(s))}{(' · ' + _e(badge)) if badge else ''}</div>
  <a href="{paper_url}#story-{s['id']}" style="display:block;margin-top:4px;font-size:18px;line-height:1.3;font-weight:600;color:#1d1d1f;text-decoration:none">{_e(s['headline'])}</a>
  <div style="margin-top:6px;font-family:{serif};font-size:15px;line-height:1.5;color:#333">{_e(s.get('summary', ''))[:260]}</div>
  <div style="margin-top:6px;font-size:12px;color:#7a7a7a">{_e(s.get('source'))}{(' · ' + _e(s['why'])) if s.get('why') else ''}</div>
</td></tr>"""

    lead_html = ""
    if lead:
        img = (f'<img src="{_e(lead["image"])}" alt="" width="560" style="display:block;width:100%;max-width:560px;'
               f'height:auto;border-radius:12px;margin:0 0 14px">') if lead.get("image") else ""
        lead_html = f"""
<tr><td style="padding:8px 0 20px">
  {img}
  <div style="font-size:12px;font-weight:600;color:#0066cc">{_e(_topic(lead))}</div>
  <a href="{paper_url}#story-{lead['id']}" style="display:block;margin-top:6px;font-size:26px;line-height:1.2;font-weight:700;color:#1d1d1f;text-decoration:none">{_e(lead['headline'])}</a>
  <div style="margin-top:10px;font-family:{serif};font-size:17px;line-height:1.55;color:#333">{_e(lead.get('summary', ''))}</div>
  {f'<div style="margin-top:8px;font-size:13px;color:#6e6e73">Why this story: {_e(lead["why"])}</div>' if lead.get('why') else ''}
</td></tr>"""

    things = paper.get("three_things") or []
    things_html = "".join(
        f'<tr><td style="padding:6px 0;font-size:15px;line-height:1.45;color:#1d1d1f"><span style="color:#2997ff;font-weight:700">{i}</span>&nbsp;&nbsp;{_e(t["text"])}</td></tr>'
        for i, t in enumerate(things[:3], 1))

    html_body = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{_e(subject)}</title></head>
<body style="margin:0;background:#f5f5f7;font-family:{font};color:#1d1d1f">
<div style="display:none;max-height:0;overflow:hidden">{_e(paper.get('editor_note', ''))[:140]}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f7"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:18px">
<tr><td style="padding:28px 28px 8px">
  <table role="presentation" width="100%"><tr>
    <td style="font-size:12px;color:#7a7a7a">No. {_e(paper.get('number', ''))}</td>
    <td align="center" style="font-size:12px;color:#1d1d1f">{_e(when)}</td>
    <td align="right" style="font-size:12px;color:#7a7a7a">{_e(reader.get('city', ''))}</td></tr></table>
  <div style="text-align:center;font-family:{serif};font-size:44px;font-weight:700;letter-spacing:-1px;margin:14px 0 2px">ParhLo</div>
  <div style="text-align:center;font-size:13px;color:#6e6e73">For {_e(reader.get('name', ''))}</div>
  <div style="border-top:3px double #1d1d1f;margin:16px 0 0"></div>
  {f'<div style="margin-top:12px;text-align:center;font-size:13px;color:#6e6e73">{_e(morning)}</div>' if morning else ''}
  {f'<div style="margin-top:14px;text-align:center;font-family:{serif};font-size:16px;line-height:1.5;color:#333">{_e(paper.get("editor_note"))}</div>' if paper.get('editor_note') else ''}
</td></tr>
<tr><td style="padding:12px 28px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{lead_html}{''.join(story_row(s) for s in rest)}</table></td></tr>
{f'<tr><td style="padding:8px 28px 0"><table role="presentation" width="100%" style="background:#272729;border-radius:14px"><tr><td style="padding:18px 20px"><div style="font-size:13px;font-weight:600;color:#2997ff;margin-bottom:6px">3 things to remember</div><table role="presentation" width="100%" style="color:#fff">{things_html.replace("color:#1d1d1f", "color:#ffffff")}</table></td></tr></table></td></tr>' if things_html else ''}
<tr><td align="center" style="padding:28px">
  <a href="{paper_url}" style="display:inline-block;background:#0066cc;color:#ffffff;text-decoration:none;font-size:17px;padding:12px 26px;border-radius:999px">Read your paper</a>
  <div style="margin-top:12px;font-size:14px"><a href="{pdf_url}" style="color:#0066cc;text-decoration:none">{pdf_label}</a></div>
</td></tr>
</table>
<table role="presentation" width="100%" style="max-width:600px"><tr><td style="padding:18px 12px;text-align:center;font-size:12px;line-height:1.5;color:#7a7a7a">
  Summaries are written by AI from the linked articles and checked against them. They can still contain mistakes.<br>
  You get this because your morning email is on. <a href="{unsubscribe_url(user['id'])}" style="color:#7a7a7a">Unsubscribe</a> ·
  <a href="{base}/dashboard" style="color:#7a7a7a">Settings</a> · <a href="{base}/privacy" style="color:#7a7a7a">Privacy</a>
</td></tr></table>
</td></tr></table></body></html>"""

    lines = [f"ParhLo · {when} · For {reader.get('name', '')}", ""]
    if morning:
        lines += [morning, ""]
    if paper.get("editor_note"):
        lines += [paper["editor_note"], ""]
    for s in ([lead] if lead else []) + rest:
        lines += [f"{_topic(s).upper()}: {s['headline']}", s.get("summary", ""), f"{s.get('source', '')} · {paper_url}#story-{s['id']}", ""]
    lines += [f"Read your paper: {paper_url}",
              ("Your newspaper PDF is attached. Download it again: " if attached else "Download the PDF: ") + pdf_url,
              "", f"Unsubscribe: {unsubscribe_url(user['id'])}"]
    return subject, html_body, "\n".join(lines)


# ---------- queue ----------

def enqueue(conn, user: dict, edition_id: int, kind: str = "morning") -> int | None:
    """Queue one email; returns the job id (None if already queued for this paper or the reader opted out)."""
    if kind == "morning" and (user.get("is_demo") or not user.get("email") or not user.get("email_morning", True)):
        return None
    row = conn.execute(
        """insert into email_jobs (user_id, edition_id, kind) values (%s,%s,%s)
           on conflict do nothing returning id""", (user["id"], edition_id, kind)).fetchone()
    return row["id"] if row else None


async def drain(limit: int = 200, job_ids: list[int] | None = None, budget_s: float = DRAIN_BUDGET_S) -> dict:
    """Claim due jobs and send them, the paper's PDF attached. Safe to run concurrently (SKIP LOCKED) and
    repeatedly (status per job). Jobs are claimed a few at a time and claiming stops after budget_s, so a run
    never outlives the server's time limit: anything left stays queued for the next run (06:00 PKT cron)."""
    from app.parhlo.pdfstore import filename, get_pdf

    with db() as conn:
        conn.execute("update email_jobs set status = 'queued' where status = 'sending' "
                     "and claimed_at < now() - make_interval(mins => %s)", (STALE_MIN,))
    stats = {"claimed": 0, "sent": 0, "retry": 0, "failed": 0, "skipped": 0, "with_pdf": 0}
    deadline = time.monotonic() + budget_s

    async def one(job: dict) -> None:
        with db() as conn:
            user = conn.execute("select * from users where id = %s", (job["user_id"],)).fetchone()
            ed = conn.execute("select id, edition_date, data, pdf_key from editions where id = %s",
                              (job["edition_id"],)).fetchone()
        if not user or not ed or not user.get("email") or (job["kind"] == "morning" and not user["email_morning"]):
            _finish(job["id"], "skipped")
            stats["skipped"] += 1
            return
        try:
            try:
                pdf = await asyncio.wait_for(get_pdf(user, ed), timeout=PDF_TIMEOUT_S)
            except Exception as e:   # no PDF → the email still goes, with the signed link
                log.warning("no PDF for email job %s: %s", job["id"], e)
                pdf = None
            subject, body, text = render(user, ed["data"], ed["edition_date"], attached=bool(pdf))
            unsub = unsubscribe_url(user["id"])
            await send_email(user["email"], subject, body, text, headers={
                "List-Unsubscribe": f"<{unsub}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"},
                attachments=[(filename(ed["edition_date"]), pdf, "application/pdf")] if pdf else None)
            _finish(job["id"], "sent")
            stats["sent"] += 1
            stats["with_pdf"] += bool(pdf)
        except Exception as e:  # one reader's failure never blocks the rest
            log.warning("email job %s failed (attempt %s): %s", job["id"], job["attempts"], e)
            final = job["attempts"] >= MAX_ATTEMPTS
            _finish(job["id"], "failed" if final else "queued", error=str(e)[:300], retry_min=None if final else 5 * job["attempts"])
            stats["failed" if final else "retry"] += 1

    while stats["claimed"] < limit and time.monotonic() < deadline:
        batch = min(CONCURRENCY, limit - stats["claimed"])
        with db() as conn:
            jobs = conn.execute(
                f"""update email_jobs set status = 'sending', attempts = attempts + 1, claimed_at = now()
                    where id in (select id from email_jobs where status = 'queued' and run_after <= now()
                                 {'and id = any(%s)' if job_ids else ''} order by id limit %s for update skip locked)
                    returning *""", ((job_ids, batch) if job_ids else (batch,))).fetchall()
        if not jobs:
            break
        stats["claimed"] += len(jobs)
        await asyncio.gather(*(one(j) for j in jobs))
    return stats


def _finish(job_id: int, status: str, error: str | None = None, retry_min: int | None = None) -> None:
    with db() as conn:
        conn.execute(
            """update email_jobs set status = %s, last_error = coalesce(%s, last_error),
                   sent_at = case when %s = 'sent' then now() else sent_at end,
                   run_after = case when %s::int is null then run_after else now() + make_interval(mins => %s::int) end
               where id = %s""", (status, error, status, retry_min, retry_min, job_id))


def enqueue_for_date(edition_date: date) -> int:
    """Queue the morning email for every reader whose paper for this date is printed."""
    n = 0
    with db() as conn:
        rows = conn.execute(
            """select u.*, e.id as edition_id from users u join editions e on e.user_id = u.id
               where e.edition_date = %s and u.email_morning and not u.is_demo and u.email is not null""",
            (edition_date,)).fetchall()
        for r in rows:
            n += bool(enqueue(conn, r, r["edition_id"]))
    return n


async def send_now(user: dict) -> dict:
    """Dashboard "send me today's email": a manual job for the reader's latest paper, sent right away."""
    if user.get("is_demo") or not user.get("email"):
        raise AppError("Create an account with an email address to get your paper by email.", 400)
    with db() as conn:
        ed = conn.execute("select id, edition_date from editions where user_id = %s order by edition_date desc limit 1",
                          (user["id"],)).fetchone()
        if not ed:
            raise AppError("Your first paper isn't printed yet. Try again in a minute.", 409)
        recent = conn.execute("select count(*) as n from email_jobs where user_id = %s and kind = 'manual' "
                              "and created_at > now() - interval '1 hour'", (user["id"],)).fetchone()["n"]
        if recent >= MANUAL_PER_HOUR:
            raise AppError("You've asked for a few emails already. Please try again in an hour.", 429)
        job_id = enqueue(conn, user, ed["id"], kind="manual")
    stats = await drain(job_ids=[job_id])
    if not stats["sent"]:
        raise AppError("We couldn't send the email just now. We'll retry shortly.", 502)
    return {"sent": True, "to": user["email"], "date": ed["edition_date"].isoformat(), "at": datetime.now().isoformat()}


def status(user_id) -> dict:
    with db() as conn:
        last = conn.execute("select status, kind, sent_at, created_at from email_jobs where user_id = %s "
                            "order by created_at desc limit 1", (user_id,)).fetchone()
    return {"last": {**last, "sent_at": last["sent_at"].isoformat() if last and last["sent_at"] else None,
                     "created_at": last["created_at"].isoformat()} if last else None}
