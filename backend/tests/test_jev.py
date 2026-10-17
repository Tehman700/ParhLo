"""Jev decision layer: parsing, fallbacks, summary checks and common-core selection (offline, fake Jev)."""

import numpy as np
import pytest

from app.parhlo import jev, rank, summarize
from app.parhlo.ingest import merge_topics


@pytest.fixture
def fake_jev(monkeypatch):
    """Make Jev 'enabled' and return canned answers instead of calling the API."""
    state = {"answers": None, "calls": []}

    async def ask(st, questions, client=None):
        state["calls"].append((st, questions))
        return state["answers"]

    monkeypatch.setattr(jev, "enabled", lambda: True)
    monkeypatch.setattr(jev, "ask", ask)
    return state


async def test_classify_parses_topic_junk_importance(fake_jev):
    fake_jev["answers"] = {
        "topic": {"type": "choice", "choice": "cricket", "confidence": 0.91,
                  "probabilities": {"cricket": 0.62, "pakistan": 0.3, "world": 0.08}},
        "junk": {"type": "noul", "noul": 0.04},
        "importance": {"type": "score", "score": 3.0, "confidence": 0.7},
    }
    d = await jev.classify_article("Babar Azam hits century", "Pakistan beat South Africa", "Dawn")
    assert d.topic == "cricket" and d.second_topic == "pakistan"  # runner-up ≥ 0.25 is kept
    assert d.junk == 0.04 and d.importance == 0.75                # score 3 of 0..4 → 0.75
    questions = fake_jev["calls"][0][1]
    assert set(questions) == {"topic", "junk", "importance"}
    assert len(questions["topic"]["criteria"]) == 17


async def test_classify_falls_back_when_jev_fails(fake_jev):
    fake_jev["answers"] = None  # timeout / 5xx / disabled
    assert await jev.classify_article("t", "e", "s") is None
    fake_jev["answers"] = {"topic": {"choice": "ai"}}  # malformed answer
    assert await jev.classify_article("t", "e", "s") is None


async def test_classify_many_is_noop_without_key():
    out = await jev.classify_many([{"title": "a", "source": "b"}] * 3)  # key blanked in conftest
    assert out == [None, None, None]


@pytest.mark.parametrize("noul,supported,confidence", [(0.08, True, 0.84), (0.98, False, 0.96), (0.5, False, 0.0)])
async def test_check_summary_mapping(fake_jev, noul, supported, confidence):
    fake_jev["answers"] = {"unsupported": {"type": "noul", "noul": noul}}
    c = await jev.check_summary("source text", "summary", ["point"])
    assert c.supported is supported and c.confidence == confidence
    instructions = fake_jev["calls"][0][1]["unsupported"]["instructions"]
    assert "summary" in instructions and "- point" in instructions["summary"]


async def test_verify_uses_jev_then_falls_back_to_llm(fake_jev, monkeypatch):
    fake_jev["answers"] = {"unsupported": {"type": "noul", "noul": 0.1}}
    r = await summarize.verify("src", "sum", [])
    assert r["by"] == "jev" and r["supported"] and r["confidence"] == 0.8

    fake_jev["answers"] = None  # Jev down → LLM verdict

    class FakeLLM:
        async def json(self, messages, schema=None, **kw):
            return schema(supported=False, unsupported_claims=["x"])

    monkeypatch.setattr(summarize, "get_llm", lambda: FakeLLM())
    r = await summarize.verify("src", "sum", [])
    assert r["by"] == "llm" and r["supported"] is False


def test_merge_topics():
    d = jev.ArticleDecision(topic="cricket", topic_confidence=0.9, second_topic="pakistan", junk=0.0, importance=0.5)
    assert merge_topics(d, ["cricket", "football"]) == ["cricket", "pakistan", "football"]


def _story(i, importance, topic_weight=0.8, cluster=1, score=None):
    v = np.zeros(8, dtype=np.float32)
    v[i % 8] = 1.0  # distinct directions → no MMR redundancy
    return {"id": i, "importance": importance, "topic_weight": topic_weight, "match_sim": 0.5,
            "cluster_size": cluster, "score": score if score is not None else 0.5 - i * 0.01,
            "embedding": v, "source": "Dawn"}


def test_common_core_picks_biggest_stories_once():
    pool = [_story(1, 0.2), _story(2, 0.3), _story(3, 0.95, topic_weight=0.1, cluster=5),
            _story(4, 0.9, topic_weight=0.1, cluster=1), _story(5, 0.4), _story(6, 0.5),
            _story(7, 0.1, topic_weight=0.1), _story(8, 0.3), _story(9, 0.2), _story(10, 0.6),
            _story(11, 0.1, topic_weight=0.05)]
    picks = rank.select_stories(pool, 10)
    core = [p["id"] for p in picks if p.get("core")]
    assert core == [3, 4]                                   # highest importance (+ coverage), even off-profile
    assert len({p["id"] for p in picks}) == len(picks)      # no story twice
    assert any(p.get("discovery") for p in picks)


def test_no_core_when_nothing_is_important():
    pool = [_story(i, 0.3) for i in range(1, 12)]
    assert not any(p.get("core") for p in rank.select_stories(pool, 10))
