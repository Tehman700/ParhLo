"""SWS quality gate: keep what some reader could get, drop spam and noise, cap per run (pure, no I/O)."""

import numpy as np

from app.parhlo.sws import outlets
from app.parhlo.sws.gate import decide


def unit(*xs):
    v = np.array(xs, np.float32)
    return v / np.linalg.norm(v)


ANCHORS = np.vstack([unit(1, 0, 0), unit(0, 1, 0)])   # two reader memories: "cricket" and "economy"


def item(title="Pakistan wins the series in Lahore today", source="smalltown.example", origin="gdelt",
         country=None, url="https://smalltown.example/a"):
    return {"title": title, "source": source, "origin": origin, "country": country, "url": url}


def test_reasons_keep_and_drop():
    items = [
        item(title="Stock price target raised (NYSE: ABC) by analysts", url="https://x.example/1"),  # promo title
        item(source="investegate.co.uk", url="https://www.investegate.co.uk/a"),                     # blocked wire
        item(title="WATCH LIVE: final stream free online tonight", url="https://y.example/2"),        # spam
        item(url="https://a.example/3", country="Uganda"),            # followed country, unrelated vector
        item(url="https://b.example/4", source="Reuters"),            # trusted outlet
        item(url="https://c.example/5"),                              # matches the cricket memory
        item(url="https://d.example/6"),                              # matches nobody
        item(url="https://e.example/7", origin="web"),                # asked for by a reader
    ]
    vectors = np.vstack([unit(1, 0, 0)] * 3 + [unit(0, 0, 1), unit(0, 0, 1), unit(0.9, 0, 0.44),
                                                  unit(0.2, 0.2, 1), unit(0, 0, 1)])
    keep, reasons = decide(items, vectors, ANCHORS, followed={"uganda"})
    assert keep == [False, False, False, True, True, True, False, True]
    assert reasons == {"blocked": 3, "followed": 1, "trusted": 1, "relevant": 1, "irrelevant": 1, "web": 1}


def test_google_news_needs_less_than_gdelt():
    vectors = np.vstack([unit(0.36, 0, 0.93)] * 2)                 # best match ≈ 0.36
    keep, _ = decide([item(origin="gnews", url="https://g/1"), item(origin="gdelt", url="https://g/2")],
                     vectors, ANCHORS, followed=set())
    assert keep == [True, False]                                    # gnews bar 0.33, gdelt bar 0.40


def test_cap_keeps_strongest_reasons_first():
    items = [item(url=f"https://r/{k}") for k in range(3)] + [item(url="https://r/f", country="Uganda")]
    vectors = np.vstack([unit(1, 0, 0.1), unit(1, 0, 0.5), unit(1, 0, 0.3), unit(0, 0, 1)])
    keep, reasons = decide(items, vectors, ANCHORS, followed={"uganda"}, max_keep=2)
    assert keep == [True, False, False, True]                       # followed beats relevance; best match next
    assert reasons["over_cap"] == 2


def test_no_readers_yet_keeps_only_trusted_and_followed():
    keep, _ = decide([item(url="https://n/1"), item(url="https://n/2", source="BBC News")],
                     np.vstack([unit(1, 0, 0)] * 2), np.zeros((0, 3), np.float32), followed=set())
    assert keep == [False, True]


def test_outlet_names_from_domains():
    assert outlets.outlet_name("https://www.reuters.com/world/x") == "Reuters"
    assert outlets.outlet_name("edition.cnn.com") == "CNN"
    assert outlets.outlet_name("https://www.monitor.co.ug/uganda/news") == "Daily Monitor"
    assert outlets.outlet_name("smalltown.example") == "smalltown.example"
