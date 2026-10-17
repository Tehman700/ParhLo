"""Ask your paper: routing a question to stories (Jev, with a keyword fallback when Jev is unavailable)."""

import asyncio

from app.parhlo import ask

STORIES = [
    {"id": 1, "headline": "Petrol price cut by Rs3.93 per litre", "summary": "The government cut the petrol price for two weeks."},
    {"id": 2, "headline": "Nvidia launches Arm laptop chip for local AI", "summary": "Nvidia's RTX Spark N1X powers laptops."},
    {"id": 3, "headline": "Pakistan beat Australia in Lahore Test", "summary": "Pakistan won the cricket Test by six wickets."},
]


def run(coro):
    return asyncio.run(coro)


def test_jev_route_picks_confident_stories(monkeypatch):
    async def fake(state, questions):
        assert set(questions["focus"]["criteria"]) == {"s1", "s2", "s3", "whole_paper", "not_in_paper"}
        return {"focus": {"choice": "s2", "confidence": 0.9, "probabilities": {"s2": 0.7, "s1": 0.25, "s3": 0.05}}}
    monkeypatch.setattr(ask.jev, "ask", fake)
    focus, info = run(ask.route("How fast is the new Nvidia chip?", STORIES, None))
    assert focus == [2, 1] and info["by"] == "jev" and info["choice"] == "s2"


def test_story_opened_from_is_always_in_focus(monkeypatch):
    async def fake(state, questions):
        assert state["reader_is_looking_at"].startswith("Pakistan beat")
        return {"focus": {"choice": "whole_paper", "confidence": 0.8, "probabilities": {"whole_paper": 0.8, "s1": 0.1}}}
    monkeypatch.setattr(ask.jev, "ask", fake)
    focus, _ = run(ask.route("Explain this simply", STORIES, 3))
    assert focus == [3]


def test_keyword_fallback_when_jev_is_down(monkeypatch):
    async def down(state, questions):
        return None
    monkeypatch.setattr(ask.jev, "ask", down)
    focus, info = run(ask.route("Why was the petrol price cut?", STORIES, None))
    assert info["by"] == "keywords" and focus[0] == 1


def test_offers_are_not_follow_ups():
    assert ask.OFFER.match("Would you like more tech news?")
    assert not ask.OFFER.match("What happens next with petrol prices?")
