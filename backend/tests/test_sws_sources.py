"""SWS source adapters: GDELT GKG parsing, Google News editions, Tavily results (offline, sample data)."""

from datetime import datetime, timedelta, timezone

from app.parhlo.ingest import parse_feed
from app.parhlo.sws import gdelt, gnews, tavily


def gkg_line(url="https://www.monitor.co.ug/news/1", source="monitor.co.ug", collection="1",
             title="Museveni names new cabinet after election", date="20261019074500",
             locations="1#Uganda#UG#UG##1#32#UG#10;4#Kampala, Kampala, Uganda#UG#UG18##0.3#32.5#-1#40;"
                       "1#Kenya#KE#KE##1#38#KE#90",
             image="https://img.example/ug.jpg") -> str:
    cols = [""] * 27
    cols[0], cols[gdelt.DATE], cols[gdelt.COLLECTION], cols[gdelt.SOURCE], cols[gdelt.URL] = \
        f"{date}-1", date, collection, source, url
    cols[gdelt.LOCATIONS], cols[gdelt.IMAGE] = locations, image
    cols[gdelt.EXTRAS] = f"<PAGE_LINKS>x</PAGE_LINKS><PAGE_TITLE>{title}</PAGE_TITLE>"
    return "\t".join(cols)


def test_gkg_parses_title_country_image_and_time():
    [item] = gdelt.parse_gkg(gkg_line())
    assert item["title"] == "Museveni names new cabinet after election"
    assert item["country"] == "Uganda"                     # Uganda is mentioned twice, Kenya once
    assert item["source"] == "Daily Monitor" and item["image"] == "https://img.example/ug.jpg"
    assert item["origin"] == "gdelt" and item["language"] == "en" and item["region"] == "global"
    assert item["published"] == datetime(2026, 10, 19, 7, 45, tzinfo=timezone.utc)
    assert item["summary"] == "" and item["hints"] == []


def test_gkg_skips_non_web_short_titles_and_duplicates():
    text = "\n".join([
        gkg_line(collection="2"),                                   # not a web article
        gkg_line(url="https://a.example/1", title="Home &amp; Away"),  # too few words (section page)
        gkg_line(url="https://a.example/2"),
        gkg_line(url="https://a.example/2"),                        # same URL twice
        "short\tline",
    ])
    items = gdelt.parse_gkg(text)
    assert [i["url"] for i in items] == ["https://a.example/2"]


def test_gkg_pakistan_region_and_unknown_country():
    [pk] = gdelt.parse_gkg(gkg_line(locations="4#Lahore, Punjab, Pakistan#PK#PK04##31#74#-1#5"))
    assert pk["country"] == "Pakistan" and pk["region"] == "pakistan"
    [none] = gdelt.parse_gkg(gkg_line(locations=""))
    assert none["country"] is None


def test_gkg_slot_names_round_trip():
    t = gdelt.slot_time("20261019081500")
    assert gdelt.slot_name(t - gdelt.STEP) == "20261019080000"


RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Bobi Wine rallies supporters in Kampala ahead of vote - Daily Monitor</title>
<link>https://news.google.com/rss/articles/abc</link><source url="https://monitor.co.ug">Daily Monitor</source>
<pubDate>%s</pubDate><description>Opposition leader addresses crowds</description></item>
</channel></rss>"""


def test_gnews_edition_feed_sets_country_and_origin():
    feed = gnews.edition_feed("UG")
    assert feed["url"] == "https://news.google.com/rss?hl=en-UG&gl=UG&ceid=UG:en"
    when = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    [item] = parse_feed(feed, RSS % when.encode())
    assert item["source"] == "Daily Monitor"                       # real outlet, not "Google News"
    assert item["title"] == "Bobi Wine rallies supporters in Kampala ahead of vote"
    assert item["country"] == "Uganda" and item["origin"] == "gnews" and item["region"] == "global"
    assert gnews.edition_feed("PK")["region"] == "pakistan"


def test_gnews_country_search_and_follow_search():
    feed = gnews.country_search_feed("Bangladesh")
    assert "q=%22Bangladesh%22%20when%3A1d" in feed["url"] and "ceid=US:en" in feed["url"]
    assert feed["country"] == "Bangladesh" and feed["origin"] == "gnews"
    assert not set(gnews.EDITIONS.values()) & set(gnews.COUNTRIES)  # each country covered one way only
    assert gnews.search_feed("Babar Azam")["origin"] == "gnews"


def test_curated_rss_items_keep_rss_origin():
    feed = {"name": "Dawn", "url": "x", "region": "pakistan", "topics": ["pakistan"]}
    when = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    [item] = parse_feed(feed, (RSS % when.encode()).replace(b" - Daily Monitor", b""))
    assert item["origin"] == "rss" and item["country"] is None and item["language"] == "en"


def test_tavily_results_to_items():
    now = datetime.now(timezone.utc)
    data = {"results": [
        {"url": "https://www.monitor.co.ug/uganda/news/x", "title": "Uganda seeks new IMF programme",
         "content": "Uganda's finance ministry said…", "published_date": now.strftime("%a, %d %b %Y %H:%M:%S GMT")},
        {"url": "https://old.example/y", "title": "Old story about Uganda politics",
         "content": "…", "published_date": (now - timedelta(days=5)).strftime("%a, %d %b %Y %H:%M:%S GMT")},
        {"url": "https://nodate.example/z", "title": "Undated story on Kampala traffic", "content": ""},
        {"url": "", "title": "no url"},
    ]}
    items = tavily.to_items(data)
    assert [i["source"] for i in items] == ["Daily Monitor", "nodate.example"]   # 5-day-old one dropped
    assert items[0]["origin"] == "web" and items[0]["summary"].startswith("Uganda's finance ministry")
    assert items[1]["published"] is None


async def test_tavily_off_without_key():
    assert await tavily.search("anything") == []                # key is blank in tests
