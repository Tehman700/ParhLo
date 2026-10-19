"""Outlet names and trust for SWS: GDELT and web search give domains ("reuters.com"); papers show names ("Reuters").

WORLD_GOOD extends ranking's KNOWN_GOOD (rank.py) with established outlets from around the world, so worldwide
stories from them rank like the ones we already trust. BLOCKED_DOMAINS / PROMO_TITLE stop press-release and
auto-generated stock pages before they cost anything (they match "business" interests surprisingly well).
"""

import re
from urllib.parse import urlparse

DOMAIN_NAMES: dict[str, str] = {
    # Already curated or trusted (names as used in rank.CURATED / KNOWN_GOOD)
    "dawn.com": "Dawn", "tribune.com.pk": "Express Tribune", "geo.tv": "Geo News", "thenews.com.pk": "The News",
    "brecorder.com": "Business Recorder", "bbc.co.uk": "BBC News", "bbc.com": "BBC News",
    "theguardian.com": "The Guardian", "nytimes.com": "The New York Times", "techcrunch.com": "TechCrunch",
    "theverge.com": "The Verge", "arstechnica.com": "Ars Technica", "espncricinfo.com": "ESPNcricinfo",
    "reuters.com": "Reuters", "apnews.com": "AP News", "aljazeera.com": "Al Jazeera", "cnn.com": "CNN",
    "cnbc.com": "CNBC", "bloomberg.com": "Bloomberg", "ft.com": "Financial Times", "economist.com": "The Economist",
    "formula1.com": "Formula 1", "motorsport.com": "Motorsport.com", "the-race.com": "The Race",
    "skysports.com": "Sky Sports", "wired.com": "Wired", "technologyreview.com": "MIT Technology Review",
    "timesofindia.indiatimes.com": "The Times of India", "hindustantimes.com": "Hindustan Times",
    "nature.com": "Nature", "science.org": "Science", "npr.org": "NPR", "washingtonpost.com": "The Washington Post",
    "forbes.com": "Forbes", "fortune.com": "Fortune", "axios.com": "Axios", "politico.com": "Politico",
    "pakistantoday.com.pk": "Pakistan Today", "arynews.tv": "ARY News", "samaa.tv": "Samaa TV",
    "arabnews.com": "Arab News",
    # Worldwide (WORLD_GOOD)
    "france24.com": "France 24", "dw.com": "DW", "euronews.com": "Euronews", "abc.net.au": "ABC News Australia",
    "cbc.ca": "CBC News", "theglobeandmail.com": "The Globe and Mail", "scmp.com": "South China Morning Post",
    "straitstimes.com": "The Straits Times", "japantimes.co.jp": "The Japan Times", "thehindu.com": "The Hindu",
    "indianexpress.com": "The Indian Express", "thedailystar.net": "The Daily Star", "kathmandupost.com":
    "The Kathmandu Post", "rappler.com": "Rappler", "kyivindependent.com": "The Kyiv Independent",
    "timesofisrael.com": "The Times of Israel", "thenationalnews.com": "The National", "gulfnews.com": "Gulf News",
    "khaleejtimes.com": "Khaleej Times", "monitor.co.ug": "Daily Monitor", "newvision.co.ug": "New Vision",
    "nation.africa": "Nation", "theeastafrican.co.ke": "The EastAfrican", "premiumtimesng.com": "Premium Times",
    "punchng.com": "Punch", "news24.com": "News24", "dailymaverick.co.za": "Daily Maverick",
    "businessday.ng": "BusinessDay", "theafricareport.com": "The Africa Report", "semafor.com": "Semafor",
    "lemonde.fr": "Le Monde", "elpais.com": "El País", "spiegel.de": "Der Spiegel", "nikkei.com": "Nikkei Asia",
    "asia.nikkei.com": "Nikkei Asia", "theatlantic.com": "The Atlantic", "wsj.com": "The Wall Street Journal",
    "independent.co.uk": "The Independent", "telegraph.co.uk": "The Telegraph", "sky.com": "Sky News",
    "abcnews.go.com": "ABC News", "cbsnews.com": "CBS News", "nbcnews.com": "NBC News", "pbs.org": "PBS",
    "theconversation.com": "The Conversation", "devex.com": "Devex", "voanews.com": "VOA",
}

WORLD_GOOD: set[str] = {
    "France 24", "DW", "Euronews", "ABC News Australia", "CBC News", "The Globe and Mail", "South China Morning Post",
    "The Straits Times", "The Japan Times", "The Hindu", "The Indian Express", "The Daily Star", "The Kathmandu Post",
    "Rappler", "The Kyiv Independent", "The Times of Israel", "The National", "Gulf News", "Khaleej Times",
    "Daily Monitor", "New Vision", "Nation", "The EastAfrican", "Premium Times", "Punch", "News24", "Daily Maverick",
    "BusinessDay", "The Africa Report", "Semafor", "Le Monde", "El País", "Der Spiegel", "Nikkei Asia", "The Atlantic",
    "The Wall Street Journal", "The Independent", "The Telegraph", "Sky News", "ABC News", "CBS News", "NBC News",
    "PBS", "The Conversation", "Devex", "VOA",
}

# Press-release wires and auto-generated stock/listicle sites: not news for a morning paper.
BLOCKED_DOMAINS = (
    "investegate.co.uk", "prnewswire.com", "globenewswire.com", "businesswire.com", "accessnewswire.com",
    "einpresswire.com", "newswire.ca", "openpr.com", "themarketsdaily.com", "marketbeat.com", "tickerreport.com",
    "wkrb13.com", "thelincolnianonline.com", "dailypolitical.com", "etfdailynews.com", "zolmax.com",
    "modernreaders.com", "americanbankingnews.com", "transcriptdaily.com", "thecerbatgem.com",
    "theenterpriseleader.com", "sportsperspectives.com", "boredpanda.com",
)
PROMO_TITLE = re.compile(
    r"company announcement|^form 8\.3|holding\(s\) in company|shares (sold|bought|acquired) by|"
    r"stock position|price target|\((nyse|nasdaq|lon|tsx|asx):", re.I)


def domain(url_or_host: str) -> str:
    host = urlparse(url_or_host).netloc if "://" in url_or_host else url_or_host
    return host.lower().removeprefix("www.")


def outlet_name(host: str) -> str:
    """"edition.cnn.com" → "CNN"; unknown domains keep the domain ("monitor-uganda.example")."""
    d = domain(host)
    for known, name in DOMAIN_NAMES.items():
        if d == known or d.endswith("." + known):
            return name
    return d


def blocked(source: str, url: str, title: str) -> bool:
    d = domain(url)
    return any(d == b or d.endswith("." + b) for b in BLOCKED_DOMAINS) or bool(PROMO_TITLE.search(title)) \
        or any(b in source.lower() for b in BLOCKED_DOMAINS)
