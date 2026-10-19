"""SWS run planning: the rotation covers every edition / country / followed name across runs."""

from app.parhlo.sws import gnews
from app.parhlo.sws.run import COUNTRIES_PER_RUN, EDITIONS_PER_RUN, _slice, plan_feeds


def test_slice_wraps_around():
    assert _slice([1, 2, 3, 4, 5], 0, 2) == [1, 2]
    assert _slice([1, 2, 3, 4, 5], 2, 2) == [5, 1]      # wraps
    assert _slice([1, 2], 7, 6) == [1, 2]               # never more than the list
    assert _slice([], 3, 4) == []


def test_rotation_reaches_every_edition_and_country():
    seen_editions, seen_countries = set(), set()
    runs = max(-(-len(gnews.EDITIONS) // EDITIONS_PER_RUN), -(-len(gnews.COUNTRIES) // COUNTRIES_PER_RUN))
    for run_no in range(runs):
        for feed in plan_feeds(run_no, follows=[]):
            (seen_editions if "/rss?" in feed["url"] else seen_countries).add(feed["country"])
    assert seen_editions == set(gnews.EDITIONS.values())
    assert seen_countries == set(gnews.COUNTRIES)


def test_followed_names_are_searched():
    feeds = plan_feeds(0, follows=["Uganda", "Babar Azam"])
    queries = [f.get("query") for f in feeds]
    assert "Uganda" in queries and "Babar Azam" in queries
