"""SWS source: GDELT 2.0 Global Knowledge Graph (GKG) files — worldwide news every 15 minutes, free, no key.

GDELT publishes one file per 15-minute window listing every article it saw (about 800–2,000 in English): the URL,
the outlet, the page title, a share image and every place the article mentions. We read these files instead of
GDELT's search API, which rate-limits shared cloud servers ("one request every 5 seconds", 429s in practice).
A window's file appears ~30 minutes after the window is listed, so we only take files that already exist.
"""

import html
import io
import logging
import re
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone

import httpx

from app.parhlo.sws.outlets import outlet_name

log = logging.getLogger("parhlo.sws.gdelt")

BASE = "https://data.gdeltproject.org/gdeltv2/"
LASTUPDATE = BASE + "lastupdate.txt"
STEP = timedelta(minutes=15)
LOOKBACK = 8          # windows checked behind the newest listed one (2 hours)
TITLE = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", re.S)

# GKG 2.1 columns we use (tab-separated, one article per line).
DATE, COLLECTION, SOURCE, URL, LOCATIONS, IMAGE, EXTRAS = 1, 2, 3, 4, 10, 18, 26


def slot_time(slot: str) -> datetime:
    return datetime.strptime(slot, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def slot_name(t: datetime) -> str:
    return t.strftime("%Y%m%d%H%M%S")


def main_country(v2locations: str) -> str | None:
    """The country the article mentions most. Entries look like type#Full Name#CC#ADM1#…; the country is
    the last comma-separated part of the full name ("Kampala, Kampala, Uganda" → "Uganda")."""
    counts: Counter[str] = Counter()
    for loc in (v2locations or "").split(";"):
        parts = loc.split("#")
        if len(parts) > 2 and parts[1]:
            counts[parts[1].rsplit(",", 1)[-1].strip()] += 1
    return counts.most_common(1)[0][0] if counts else None


def parse_gkg(text: str, language: str = "en") -> list[dict]:
    """One GKG file → items (web articles with a real headline only)."""
    items, seen = [], set()
    for line in text.split("\n"):
        r = line.split("\t")
        if len(r) <= EXTRAS or r[COLLECTION] != "1":   # 1 = web article
            continue
        url, m = r[URL], TITLE.search(r[EXTRAS])
        if not url.startswith("http") or not m or url in seen:
            continue
        title = re.sub(r"\s+", " ", html.unescape(m.group(1))).strip()[:300]
        if len(re.findall(r"[A-Za-z]{3,}", title)) < 4:   # skip section pages and empty titles
            continue
        seen.add(url)
        country = main_country(r[LOCATIONS])
        items.append({
            "url": url, "title": title, "source": outlet_name(r[SOURCE] or url),   # "reuters.com" → "Reuters"
            "region": "pakistan" if country == "Pakistan" else "global",
            "summary": "", "image": r[IMAGE] or None,
            "published": slot_time(r[DATE]) if re.fullmatch(r"\d{14}", r[DATE]) else None,
            "hints": [], "origin": "gdelt", "country": country, "language": language,
        })
    return items


async def newest_listed(client: httpx.AsyncClient) -> str:
    """The newest 15-minute window GDELT has announced (its file may not exist yet)."""
    r = await client.get(LASTUPDATE)
    r.raise_for_status()
    for line in r.text.splitlines():
        if line.endswith(".gkg.csv.zip"):
            return line.rsplit("/", 1)[1][:14]
    raise ValueError("no GKG file listed")


async def fetch_slot(client: httpx.AsyncClient, slot: str) -> list[dict] | None:
    """Items of one window, or None if its file isn't published yet."""
    r = await client.get(f"{BASE}{slot}.gkg.csv.zip")
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        text = z.read(z.namelist()[0]).decode("utf-8", errors="replace")
    return parse_gkg(text)


async def fetch_new(after: str | None, max_slots: int = 2, client: httpx.AsyncClient | None = None
                    ) -> tuple[list[dict], list[str]]:
    """Items from windows newer than `after` (oldest first, at most max_slots), and the windows read.
    With no `after`, only the newest published window."""
    own = client is None
    client = client or httpx.AsyncClient(timeout=60, follow_redirects=True)
    try:
        newest = slot_time(await newest_listed(client))
        candidates = [slot_name(newest - STEP * k) for k in range(LOOKBACK, -1, -1)]   # oldest → newest
        if after:
            candidates = [s for s in candidates if s > after]
        else:
            candidates = candidates[::-1]   # newest first: take the first one that exists
        items: list[dict] = []
        done: list[str] = []
        for slot in candidates:
            got = await fetch_slot(client, slot)
            if got is None:
                if after:
                    break            # files appear in order: later windows aren't ready either
                continue             # no `after`: keep walking back to the newest published file
            items += got
            done.append(slot)
            if not after or len(done) >= max_slots:
                break
        log.info("gdelt read %s → %d items", done, len(items))
        return items, done
    finally:
        if own:
            await client.aclose()
