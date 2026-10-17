"""Email via AWS SES (ap-south-1). Credentials: the app's own IAM user (PARHLO_AWS_*), else the default chain."""

import asyncio
import logging
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


def _send(to: str, subject: str, html: str, text: str) -> str:
    s = get_settings()
    try:
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
        if "not verified" in str(e):
            raise AppError("We can't email this address yet (our email service is in sandbox mode). "
                           "Use Continue with Google or try a demo reader.", 400) from e
        raise AppError("Couldn't send the email. Please try again.", 502) from e


async def send_email(to: str, subject: str, html: str, text: str) -> str:
    return await asyncio.to_thread(_send, to, subject, html, text)


def otp_email(code: str) -> tuple[str, str, str]:
    subject = f"{code} is your ParhLo code"
    text = f"Your ParhLo sign-in code is {code}. It expires in 10 minutes. If you didn't ask for it, ignore this email."
    html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,sans-serif;background:#f5f5f7;padding:32px">
  <div style="max-width:440px;margin:0 auto;background:#ffffff;border:1px solid #e0e0e0;border-radius:18px;padding:32px;color:#1d1d1f">
    <div style="font-family:Georgia,serif;font-size:28px;font-weight:700">Parh<i style="color:#0066cc">Lo</i></div>
    <p style="font-size:17px;line-height:1.47;margin:24px 0 8px">Your sign-in code:</p>
    <div style="font-size:40px;font-weight:700;letter-spacing:10px;margin:8px 0 16px">{code}</div>
    <p style="font-size:14px;color:#7a7a7a;line-height:1.43">It expires in 10 minutes. If you didn't ask for this code, you can ignore this email.</p>
  </div></div>"""
    return subject, html, text
