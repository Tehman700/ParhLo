"""Email delivery: Gmail SMTP first, AWS SES (ap-south-1) as fallback. Both reach any address, with attachments.

Gmail stays primary because our sender is a gmail.com address: sending it through SES would fail
Gmail's DMARC alignment and land in spam. SES has production access (50k/day) for when we own a domain.
"""

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from functools import lru_cache

import boto3

from app.core.config import get_settings
from app.core.errors import AppError

log = logging.getLogger("parhlo.mailer")


@lru_cache(maxsize=1)
def _ses():
    s = get_settings()
    creds = ({"aws_access_key_id": s.parhlo_aws_access_key_id, "aws_secret_access_key": s.parhlo_aws_secret_access_key}
             if s.parhlo_aws_access_key_id else {})
    return boto3.client("sesv2", region_name=s.parhlo_aws_region, **creds)


Attachment = tuple[str, bytes, str]   # (filename, content, MIME type), e.g. ("ParhLo-2026-10-19.pdf", b"%PDF…", "application/pdf")


def _message(to: str, subject: str, html: str, text: str, headers: dict | None = None,
             attachments: list[Attachment] | None = None) -> EmailMessage:
    """One MIME message (text + HTML, optional attachments), used by both Gmail and SES."""
    s = get_settings()
    msg = EmailMessage()
    msg["From"] = formataddr(("ParhLo", s.gmail_user or s.email_from))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain="parhlo.app")
    for k, v in (headers or {}).items():
        msg[k] = v
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    for filename, content, mime in attachments or []:
        maintype, subtype = mime.split("/", 1)
        msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
    return msg


def _send_gmail(msg: EmailMessage) -> str:
    s = get_settings()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(s.gmail_user, s.gmail_app_password.replace(" ", ""))
        smtp.send_message(msg)
    return msg["Message-ID"]


def _send_ses(to: str, subject: str, html: str, text: str, msg: EmailMessage, has_attachments: bool) -> str:
    s = get_settings()
    try:
        if has_attachments:   # SES "Simple" can't carry attachments: send the same MIME message raw
            del msg["From"]
            msg["From"] = f"ParhLo <{s.email_from}>"
            res = _ses().send_email(FromEmailAddress=f"ParhLo <{s.email_from}>", Destination={"ToAddresses": [to]},
                                    Content={"Raw": {"Data": msg.as_bytes()}})
        else:
            res = _ses().send_email(
                FromEmailAddress=f"ParhLo <{s.email_from}>",
                Destination={"ToAddresses": [to]},
                Content={"Simple": {"Subject": {"Data": subject, "Charset": "UTF-8"},
                                    "Body": {"Html": {"Data": html, "Charset": "UTF-8"},
                                             "Text": {"Data": text, "Charset": "UTF-8"}}}},
            )
        return res["MessageId"]
    except _ses().exceptions.MessageRejected as e:
        log.warning("SES rejected mail to %s: %s", to, e)
        raise AppError("We couldn't send an email to this address. Please check it, or continue with Google.", 400) from e


def _send(to: str, subject: str, html: str, text: str, headers: dict | None = None,
          attachments: list[Attachment] | None = None) -> str:
    s = get_settings()
    msg = _message(to, subject, html, text, headers, attachments)
    if s.gmail_user and s.gmail_app_password:
        try:
            return _send_gmail(msg)
        except (smtplib.SMTPException, OSError) as e:
            log.warning("Gmail send failed (%s); falling back to SES", e)
    return _send_ses(to, subject, html, text, msg, bool(attachments))


async def send_email(to: str, subject: str, html: str, text: str, headers: dict | None = None,
                     attachments: list[Attachment] | None = None) -> str:
    """headers: extra MIME headers such as List-Unsubscribe. attachments: e.g. the paper's PDF."""
    return await asyncio.to_thread(_send, to, subject, html, text, headers, attachments)


def otp_email(code: str) -> tuple[str, str, str]:
    subject = f"{code} is your ParhLo code"
    text = f"Your ParhLo sign-in code is {code}. It expires in 10 minutes. If you didn't ask for it, you can ignore this email."
    html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Helvetica,Arial,sans-serif;background:#f5f5f7;padding:32px 16px">
  <div style="max-width:440px;margin:0 auto;background:#ffffff;border:1px solid #e0e0e0;border-radius:18px;padding:32px;color:#1d1d1f">
    <div style="font-size:22px;font-weight:600;letter-spacing:-0.3px">ParhLo</div>
    <p style="font-size:17px;line-height:1.47;margin:24px 0 8px">Your sign-in code is:</p>
    <div style="font-size:40px;font-weight:600;letter-spacing:10px;margin:8px 0 16px">{code}</div>
    <p style="font-size:14px;color:#6e6e73;line-height:1.43;margin:0">It expires in 10 minutes. If you didn't ask for this code, you can ignore this email.</p>
  </div>
  <p style="max-width:440px;margin:16px auto 0;font-size:12px;color:#7a7a7a;text-align:center">ParhLo · Your news, in one paper.</p>
</div>"""
    return subject, html, text
