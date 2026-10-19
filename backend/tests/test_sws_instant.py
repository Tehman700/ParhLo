"""SWS on demand: requested items pass the gate; "Search the web" answers only from the results, labelled."""

from datetime import datetime, timezone

import numpy as np

from app.parhlo import ask
from app.parhlo.sws import instant, tavily
from app.parhlo.sws.gate import decide


def test_requested_items_pass_the_gate_but_spam_does_not():
    items = [
        {"title": "Museveni names a new cabinet in Kampala", "source": "smalltown.example", "origin": "gnews",
         "url": "https://s.example/1", "requested": True},
        {"title": "WATCH LIVE stream free online of the vote", "source": "spam.example", "origin": "gnews",
         "url": "https://s.example/2", "requested": True},
    ]
    keep, reasons = decide(items, np.zeros((2, 3), np.float32), np.eye(3, dtype=np.float32), followed=set())
    assert keep == [True, False]
    assert reasons["requested"] == 1 and reasons["blocked"] == 1


class FakeLLM:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    async def json(self, messages, schema=None, **kw):
        self.calls.append(messages)
        return schema.model_validate(self.reply)


async def test_ask_web_answers_from_numbered_results(monkeypatch):
    results = [{"title": "Uganda seeks new IMF programme", "source": "Daily Monitor", "url": "https://m/1",
                "summary": "Uganda asked the IMF for a new loan.", "published": datetime(2026, 10, 18, tzinfo=timezone.utc)},
               {"title": "Kampala traffic plan", "source": "New Vision", "url": "https://n/2", "summary": "…"}]
    recorded = []

    async def fake_search(query, max_results=8, days=2, client=None):
        assert days == 7
        return results
    monkeypatch.setattr(instant, "check", lambda user: True)
    monkeypatch.setattr(instant, "record", lambda *a: recorded.append(a))
    monkeypatch.setattr(tavily, "search", fake_search)
    llm = FakeLLM({"answer": "Uganda asked the IMF for a new loan programme.", "result_ids": [1, 1, 9], "found": True})
    monkeypatch.setattr(ask, "get_llm", lambda: llm)

    out = await ask.ask_web({"id": "u1"}, ask.AskIn(question="Is Uganda getting an IMF loan?"))
    assert out["from_web"] and out["found"] and not out["in_paper"]
    assert [s["url"] for s in out["sources"]] == ["https://m/1"]          # duplicates and unknown numbers dropped
    system = llm.calls[0][0]["content"]
    assert "[1] Uganda seeks new IMF programme (Daily Monitor, 18 Oct 2026)" in system and "ONLY" in system
    assert recorded and recorded[0][1] == "ask" and recorded[0][3] == 1     # one Tavily credit counted


async def test_ask_web_with_nothing_found(monkeypatch):
    async def none(*a, **k):
        return []

    async def no_feeds(feeds):
        return [], []
    monkeypatch.setattr(instant, "check", lambda user: False)               # Tavily off / over budget
    monkeypatch.setattr(instant, "record", lambda *a: None)
    monkeypatch.setattr(tavily, "search", none)
    monkeypatch.setattr("app.parhlo.ingest.fetch_all", no_feeds)
    out = await ask.ask_web({"id": "u1"}, ask.AskIn(question="Something nobody reported"))
    assert out["found"] is False and out["sources"] == [] and out["via"] == "Google News"
