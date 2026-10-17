"""Help & contact: messages from readers are stored and emailed to the team (reply goes straight to the reader)."""

import html
import logging

from pydantic import BaseModel, Field

from app.core.database import db
from app.core.errors import AppError
from app.parhlo.auth import normalize_email
from app.parhlo.mailer import send_email

log = logging.getLogger("parhlo.support")

TEAM_EMAIL = "tehmanhassan@gmail.com"
TOPICS = {
    "question": "A question",
    "problem": "Something isn't working",
    "summary": "A summary looks wrong",
    "idea": "An idea for ParhLo",
    "account": "My account or privacy",
    "sources": "Suggest a news source",
    "press": "Press or partnership",
}
PER_HOUR = 5


class SupportIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(max_length=254)
    topic: str
    message: str = Field(min_length=10, max_length=4000)
    page: str | None = Field(default=None, max_length=300)   # where they were (e.g. a story link)
    website: str | None = None                               # honeypot: people leave it empty, bots fill it


async def submit(body: SupportIn, user: dict | None) -> dict:
    if body.website:  # bot: pretend it worked
        return {"sent": True}
    if body.topic not in TOPICS:
        raise AppError("Please choose a topic.", 422)
    email = normalize_email(body.email)  # 422 if it isn't an email address
    with db() as conn:
        recent = conn.execute("select count(*) as n from support_messages where lower(email) = %s "
                              "and created_at > now() - interval '1 hour'", (email,)).fetchone()["n"]
        if recent >= PER_HOUR:
            raise AppError("You've sent a few messages already. Please try again in an hour.", 429)
        row = conn.execute(
            """insert into support_messages (user_id, name, email, topic, message, page)
               values (%s,%s,%s,%s,%s,%s) returning id""",
            (user["id"] if user else None, body.name.strip(), email, body.topic, body.message.strip(), body.page)).fetchone()
    e = html.escape
    label = TOPICS[body.topic]
    who = f"{body.name} <{email}>" + (f" · account {user['id']}" if user else " · not signed in")
    text = f"{label}\nFrom: {who}\n" + (f"Page: {body.page}\n" if body.page else "") + f"\n{body.message}\n\nMessage #{row['id']}"
    body_html = (f"<div style=\"font-family:-apple-system,Segoe UI,Arial,sans-serif;color:#1d1d1f\">"
                 f"<p style=\"font-size:13px;color:#6e6e73;margin:0\">ParhLo · Help &amp; contact · #{row['id']}</p>"
                 f"<h2 style=\"font-size:20px;margin:6px 0 4px\">{e(label)}</h2>"
                 f"<p style=\"font-size:14px;color:#6e6e73;margin:0 0 16px\">From {e(who)}"
                 f"{('<br>Page: ' + e(body.page)) if body.page else ''}</p>"
                 f"<div style=\"font-size:16px;line-height:1.5;white-space:pre-wrap;background:#f5f5f7;border-radius:12px;padding:16px\">{e(body.message)}</div>"
                 f"<p style=\"font-size:13px;color:#6e6e73\">Reply to this email to answer {e(body.name)} directly.</p></div>")
    try:
        await send_email(TEAM_EMAIL, f"[ParhLo] {label} — {body.name}", body_html, text, headers={"Reply-To": email})
    except Exception as ex:  # stored anyway; the team can read it in the database
        log.warning("support email failed for #%s: %s", row["id"], ex)
    return {"sent": True, "id": row["id"], "reply_to": email}
