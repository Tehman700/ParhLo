"""SWS query planner: busy searches run more often, quiet ones back off; breaking headlines become searches."""

from app.parhlo.ingest import parse_feed
from app.parhlo.sws import planner


def test_busy_searches_speed_up_quiet_ones_back_off():
    assert planner.adapt("follow", 30, new=5) == 15        # busy → twice as often
    assert planner.adapt("follow", 15, new=9) == 15        # never more often than every 15 min
    assert planner.adapt("follow", 30, new=0) == 60        # quiet → half as often
    assert planner.adapt("follow", 240, new=0) == 240      # never less often than every 4 h
    assert planner.adapt("country", 240, new=1) == 240     # a little news → unchanged
    assert planner.adapt("country", 720, new=0) == 720


def test_breaking_headline_to_search_keywords():
    kw = planner.keywords("Kenya confirms eighth Ebola case amid widening regional outbreak")
    assert kw == "Kenya confirms eighth Ebola case widening"   # stop words dropped, first 6 kept
    assert planner.keywords("Up to a lot") == ""


def test_each_kind_reads_the_right_feed_and_is_tagged():
    edition = planner.feed_for({"id": 1, "kind": "edition", "query": "UG"})
    country = planner.feed_for({"id": 2, "kind": "country", "query": "Bangladesh"})
    follow = planner.feed_for({"id": 3, "kind": "follow", "query": "Babar Azam"})
    assert edition["url"].endswith("ceid=UG:en") and edition["country"] == "Uganda"
    assert "%22Bangladesh%22" in country["url"] and country["country"] == "Bangladesh"
    assert "Babar%20Azam" in follow["url"]
    assert [f["query_id"] for f in (edition, country, follow)] == [1, 2, 3]


def test_items_remember_which_search_found_them():
    feed = {**planner.feed_for({"id": 7, "kind": "follow", "query": "Nvidia"})}
    rss = b"""<rss><channel><item><title>Nvidia unveils a new laptop chip for local AI - Reuters</title>
    <link>https://news.google.com/x</link><source url="https://reuters.com">Reuters</source></item></channel></rss>"""
    [item] = parse_feed(feed, rss)
    assert item["query_id"] == 7 and item["source"] == "Reuters"


def test_about_you_phrases_are_searched_on_their_own_schedule():
    feed = planner.feed_for({"id": 11, "kind": "interest", "query": "car accident news"})
    assert "car%20accident%20news" in feed["url"] and feed["query_id"] == 11
    assert planner.adapt("interest", 60, new=0) == 120 and planner.adapt("interest", 360, new=0) == 360
