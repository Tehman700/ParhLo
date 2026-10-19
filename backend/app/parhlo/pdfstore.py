"""The paper as a PDF file, made once per paper and kept in S3, for attaching to the morning email.

  stored?  editions.pdf_key set → download it from S3
  else     ask our own PDF page for it (headless Chromium, ~8 s) with a signed link (no session needed),
           store it in S3 and remember the key on the paper
A reprint or the AI polish clears pdf_key (editions.py), so an email always carries the paper as it is now.
Anything failing returns None: the email still goes out, with the signed PDF link instead.
"""

import asyncio
import hashlib
import logging
from functools import lru_cache

import boto3
import httpx

from app.core.config import get_settings
from app.core.database import db
from app.parhlo.digest import pdf_query

log = logging.getLogger("parhlo.pdfstore")
RENDER_TIMEOUT = 60.0


@lru_cache(maxsize=1)
def _s3():
    s = get_settings()
    creds = ({"aws_access_key_id": s.parhlo_aws_access_key_id, "aws_secret_access_key": s.parhlo_aws_secret_access_key}
             if s.parhlo_aws_access_key_id else {})
    return boto3.client("s3", region_name=s.parhlo_aws_region, **creds)


def filename(edition_date) -> str:
    return f"ParhLo-{edition_date.isoformat()}.pdf"


async def get_pdf(user: dict, ed: dict) -> bytes | None:
    """ed: the editions row (id, edition_date, data, pdf_key). Returns the PDF bytes, or None."""
    bucket = get_settings().s3_bucket
    if ed.get("pdf_key"):
        try:
            obj = await asyncio.to_thread(lambda: _s3().get_object(Bucket=bucket, Key=ed["pdf_key"]))
            return await asyncio.to_thread(obj["Body"].read)
        except Exception as e:
            log.warning("stored PDF %s unreadable (%s); rendering again", ed["pdf_key"], e)
    day = ed["edition_date"].isoformat()
    url = f"{get_settings().public_url.rstrip('/')}/pdf/{day}?{pdf_query(user['id'], day)}"
    try:
        async with httpx.AsyncClient(timeout=RENDER_TIMEOUT) as client:
            r = await client.get(url)
    except httpx.HTTPError as e:
        log.warning("PDF render failed for %s %s: %s", user["id"], day, e)
        return None
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        log.warning("PDF render failed for %s %s: HTTP %s", user["id"], day, r.status_code)
        return None
    version = (ed.get("data") or {}).get("generated_at", "")
    key = f"pdf/{user['id']}/{day}-{hashlib.sha1(version.encode()).hexdigest()[:10]}.pdf"
    try:
        await asyncio.to_thread(lambda: _s3().put_object(Bucket=bucket, Key=key, Body=r.content,
                                                         ContentType="application/pdf"))
        with db() as conn:   # only if the paper hasn't been reprinted meanwhile
            conn.execute("update editions set pdf_key = %s where id = %s and data->>'generated_at' = %s",
                         (key, ed["id"], version))
    except Exception as e:
        log.warning("couldn't store PDF %s: %s", key, e)   # still attach this one
    return r.content
