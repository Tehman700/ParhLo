"""Curated RSS sources (all verified live on 2026-10-17) + Google News search for niche interests."""

from urllib.parse import quote

# ── INGEST STEP 2 ── The sources: 28 curated RSS feeds (Pakistani + global outlets).
# Each feed is a dict with:
#   name     → outlet name shown on the story ("Dawn", "BBC News"…)
#   url      → the RSS feed address
#   region   → "pakistan" or "global"; used later by ranking for the reader's Pakistan/world mix
#   topics   → topic HINTS for everything in this feed (e.g. a cricket feed → "cricket"); merged with Jev's decision
#   fallback → (domain, section) for outlets that block cloud servers (Dawn blocks Vercel's IPs):
#              if the direct feed fails, we fetch the same outlet's stories through Google News (google_news_site)
# Why RSS: free, legal, structured (title, link, summary, date, image), and every major outlet publishes it.
FEEDS: list[dict] = [
    # Pakistan
    {"name": "Dawn", "url": "https://www.dawn.com/feeds/home", "region": "pakistan", "topics": [], "fallback": ("dawn.com", "")},
    {"name": "Dawn", "url": "https://www.dawn.com/feeds/pakistan", "region": "pakistan", "topics": ["pakistan"], "fallback": ("dawn.com", "pakistan")},
    {"name": "Dawn", "url": "https://www.dawn.com/feeds/business", "region": "pakistan", "topics": ["business"], "fallback": ("dawn.com", "business")},
    {"name": "Dawn", "url": "https://www.dawn.com/feeds/sport", "region": "pakistan", "topics": [], "fallback": ("dawn.com", "sport")},
    {"name": "Dawn", "url": "https://www.dawn.com/feeds/world", "region": "pakistan", "topics": ["world"], "fallback": ("dawn.com", "world")},
    {"name": "Express Tribune", "url": "https://tribune.com.pk/feed/home", "region": "pakistan", "topics": []},
    {"name": "Business Recorder", "url": "https://www.brecorder.com/feeds/latest-news", "region": "pakistan", "topics": ["economy"]},
    {"name": "Geo News", "url": "https://www.geo.tv/rss/1/1", "region": "pakistan", "topics": []},
    {"name": "The News", "url": "https://www.thenews.com.pk/rss/1/1", "region": "pakistan", "topics": []},
    # Global
    {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "region": "global", "topics": ["world"]},
    {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "region": "global", "topics": ["technology"]},
    {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "region": "global", "topics": ["science"]},
    {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/health/rss.xml", "region": "global", "topics": ["health"]},
    {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss", "region": "global", "topics": ["world"]},
    {"name": "The Guardian", "url": "https://www.theguardian.com/business/rss", "region": "global", "topics": ["business"]},
    {"name": "The Guardian", "url": "https://www.theguardian.com/culture/rss", "region": "global", "topics": ["culture"]},
    {"name": "The New York Times", "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "region": "global", "topics": []},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "region": "global", "topics": ["technology"]},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "region": "global", "topics": ["technology"]},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "region": "global", "topics": ["technology"]},
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage", "region": "global", "topics": ["technology"]},
    {"name": "ESPNcricinfo", "url": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml", "region": "global", "topics": ["cricket"]},
    {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/football/rss.xml", "region": "global", "topics": ["football"]},
    {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/formula1/rss.xml", "region": "global", "topics": ["motorsport"]},
    {"name": "Autosport", "url": "https://www.autosport.com/rss/f1/news/", "region": "global", "topics": ["motorsport"]},
    {"name": "Motorsport.com", "url": "https://www.motorsport.com/rss/f1/news/", "region": "global", "topics": ["motorsport"]},
    {"name": "The Race", "url": "https://www.the-race.com/feed/", "region": "global", "topics": ["motorsport"]},
    {"name": "Formula 1", "url": "https://www.formula1.com/en/latest/all.xml", "region": "global", "topics": ["motorsport"]},
]


def google_news_site(domain: str, name: str, region: str, topics: list[str], extra: str = "") -> dict:
    """Fallback for outlets that block cloud IPs: the outlet's latest stories via Google News search."""
    # e.g. "site:dawn.com pakistan" → Google News returns Dawn's own latest Pakistan stories.
    feed = google_news_feed(f"site:{domain} {extra}".strip())
    # "outlet" tells parse_feed to show the real outlet name (Dawn), not "Google News".
    # origin stays "rss": it's still one of our curated outlets, just fetched through Google News.
    return {**feed, "name": name, "region": region, "topics": topics, "outlet": name, "origin": "rss"}


def google_news_feed(query: str, edition: str = "PK") -> dict:
    """Google News search RSS (English, one country edition, last day) — covers any niche interest."""
    # Used for every name readers follow (STEP 1 passes them in). "when:1d" = only the last 24 hours;
    # hl/gl/ceid = English, the chosen country edition (Pakistan by default, so results suit a Pakistani reader).
    q = quote(f"{query} when:1d")
    return {
        "name": "Google News",
        "url": f"https://news.google.com/rss/search?q={q}&hl=en-{edition}&gl={edition}&ceid={edition}:en",
        "region": "global",
        "topics": [],
        "query": query,
        "origin": "gnews",
    }
