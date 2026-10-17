"""Curated RSS sources (all verified live on 2026-10-17) + Google News search for niche interests."""

from urllib.parse import quote

# name, url, region, topic hints
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
    feed = google_news_feed(f"site:{domain} {extra}".strip())
    return {**feed, "name": name, "region": region, "topics": topics, "outlet": name}


def google_news_feed(query: str) -> dict:
    """Google News search RSS (Pakistan edition, last day) — covers any niche interest."""
    q = quote(f"{query} when:1d")
    return {
        "name": "Google News",
        "url": f"https://news.google.com/rss/search?q={q}&hl=en-PK&gl=PK&ceid=PK:en",
        "region": "global",
        "topics": [],
        "query": query,
    }
