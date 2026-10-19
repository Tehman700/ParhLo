"""Enrichment: the real publisher link, a share image and the full text for stories that arrive without them.

Google News gives coded redirect links (news.google.com/rss/articles/CBMi…) and no images, so its stories had no
picture, no full text and only one-line summaries. For each story that needs it:
  1. Google News link → the publisher's real URL (Google's own "garturlreq" lookup: read the article page's
     signature + timestamp, then one batchexecute POST for many links at once)
  2. open the real page once → its share image (og:image / twitter:image) and the article text (trafilatura)
Free (no API), runs only on stories we keep, and anything that fails just leaves the story as it was.
"""

import asyncio
import json
import logging
import re
from urllib.parse import parse_qs, quote, urlparse

import httpx
import trafilatura

log = logging.getLogger("parhlo.sws.enrich")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
BATCHEXECUTE = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
_SG, _TS = re.compile(r'data-n-a-sg="([^"]+)"'), re.compile(r'data-n-a-ts="([^"]+)"')
_CTX = [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1],
        "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0]
MIN_TEXT = 600            # shorter extractions are usually cookie walls or teasers
CONCURRENCY = 8
_META = re.compile(r"<meta\b[^>]*>", re.I)
_ATTR = re.compile(r'([a-zA-Z:_-]+)\s*=\s*["\']([^"\']*)["\']')
_NOT_A_PHOTO = re.compile(r"logo|favicon|placeholder|default[-_]?(image|share|og)|blank\.|spacer|\.svg(\?|$)", re.I)


def gn_id(url: str) -> str | None:
    """The article id of a Google News link, or None if it isn't one."""
    u = urlparse(url)
    parts = u.path.split("/")
    if u.hostname == "news.google.com" and len(parts) > 1 and parts[-2] in ("articles", "read"):
        return parts[-1] or None
    return None


def share_image(html: str, base: str = "") -> str | None:
    """The page's share image: og:image, then twitter:image — skipping logos and placeholders."""
    found: dict[str, str] = {}
    for tag in _META.findall(html[:200_000]):
        attrs = {k.lower(): v for k, v in _ATTR.findall(tag)}
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key in ("og:image", "og:image:url", "og:image:secure_url", "twitter:image", "twitter:image:src") \
                and attrs.get("content") and key not in found:
            found[key] = attrs["content"].strip()
    for key in ("og:image:secure_url", "og:image", "og:image:url", "twitter:image", "twitter:image:src"):
        img = found.get(key)
        if img and not _NOT_A_PHOTO.search(img):
            if img.startswith("//"):
                img = "https:" + img
            elif img.startswith("/") and base:
                u = urlparse(base)
                img = f"{u.scheme}://{u.netloc}{img}"
            return img if img.startswith("http") else None
    return None


async def _params(client: httpx.AsyncClient, url: str, gid: str) -> tuple[str, str] | None:
    q = parse_qs(urlparse(url).query)
    loc = "&".join(f"{k}={quote(q[k][0])}" for k in ("hl", "gl", "ceid") if k in q) or "hl=en-US&gl=US&ceid=US:en"
    r = await client.get(f"https://news.google.com/rss/articles/{gid}?{loc}", follow_redirects=True)
    sg, ts = _SG.search(r.text), _TS.search(r.text)
    return (sg.group(1), ts.group(1)) if sg and ts else None


async def decode_many(client: httpx.AsyncClient, urls: list[str]) -> dict[str, str]:
    """Google News links → publisher URLs (the ones that decode). One POST for all of them."""
    sem = asyncio.Semaphore(CONCURRENCY)
    pending: list[tuple[str, str, str, str]] = []   # (url, id, timestamp, signature)

    async def one(url: str) -> None:
        gid = gn_id(url)
        if not gid:
            return
        try:
            async with sem:
                p = await _params(client, url, gid)
            if p:
                pending.append((url, gid, p[1], p[0]))
        except httpx.HTTPError as e:
            log.debug("google news params failed for %s: %s", url, e)

    await asyncio.gather(*(one(u) for u in urls))
    if not pending:
        return {}
    envelopes = [["Fbv4je", json.dumps(["garturlreq", _CTX, gid, int(ts) if ts.isdigit() else ts, sig],
                                       separators=(",", ":")), None, str(n)]
                 for n, (_, gid, ts, sig) in enumerate(pending)]
    try:
        r = await client.post(BATCHEXECUTE, content="f.req=" + quote(json.dumps([envelopes], separators=(",", ":"))),
                              headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
        r.raise_for_status()
        pairs = parse_batchexecute(r.text)
    except (httpx.HTTPError, ValueError) as e:
        log.warning("google news decode failed: %s", e)
        return {}
    by_req = {req: real for req, real in pairs if req is not None}
    return {pending[int(req)][0]: real for req, real in by_req.items()
            if req.isdigit() and int(req) < len(pending) and real.startswith("http")}


def parse_batchexecute(text: str) -> list[tuple[str | None, str]]:
    """(request id, decoded URL) pairs from Google's batchexecute response."""
    body = text.split("\n\n", 1)[1] if "\n\n" in text else text
    body = body.lstrip()
    if body.startswith(")]}'"):
        body = body.split("\n", 1)[1] if "\n" in body else body[4:]
    rows = json.loads(body.strip())
    pairs = []
    for row in rows:
        if isinstance(row, list) and len(row) >= 3 and (row[0] == "wrb.fr" or row[1] == "Fbv4je"):
            payload = json.loads(row[2]) if isinstance(row[2], str) else row[2]
            if isinstance(payload, list) and payload and payload[0] == "garturlres":
                req = next((str(c) for c in reversed(row[3:]) if c is not None), None)
                pairs.append((req, payload[1]))
    return pairs


async def _page(client: httpx.AsyncClient, url: str) -> tuple[str | None, str | None]:
    """(share image, article text) of a publisher page."""
    r = await client.get(url, follow_redirects=True)
    if r.status_code != 200 or "html" not in r.headers.get("content-type", "html"):
        return None, None
    text = await asyncio.to_thread(trafilatura.extract, r.text, include_comments=False, include_tables=False)
    return share_image(r.text, str(r.url)), (text if text and len(text) >= MIN_TEXT else None)


async def enrich(items: list[dict], timeout: float = 12.0) -> dict:
    """Fill in link / image / content (in place) for items missing an image or text. Returns counts."""
    todo = [i for i in items if not i.get("image") or not i.get("content")]
    stats = {"tried": len(todo), "decoded": 0, "images": 0, "texts": 0}
    if not todo:
        return stats
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": UA}, follow_redirects=True) as client:
        google = [i for i in todo if gn_id(i.get("link") or i["url"]) and not i.get("link")]
        real = await decode_many(client, [i["url"] for i in google])
        for i in google:
            if i["url"] in real:
                i["link"] = real[i["url"]]
                stats["decoded"] += 1
        sem = asyncio.Semaphore(CONCURRENCY)

        async def one(i: dict) -> None:
            target = i.get("link") or i["url"]
            if gn_id(target):
                return                       # couldn't decode: Google's page has nothing of the article
            try:
                async with sem:
                    img, text = await _page(client, target)
            except Exception as e:           # one bad page never stops the rest
                log.debug("page fetch failed for %s: %s", target, e)
                return
            if img and not i.get("image"):
                i["image"] = img
                stats["images"] += 1
            if text and not i.get("content"):
                i["content"] = text
                stats["texts"] += 1

        await asyncio.gather(*(one(i) for i in todo))
    return stats
