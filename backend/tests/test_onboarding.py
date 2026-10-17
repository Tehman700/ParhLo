"""Onboarding headline selection: chosen topics first (round-robin), then discovery from other topics."""

from app.parhlo.profile import _pick


def _row(i, topic, importance):
    return {"id": i, "title": f"Story {i} about {topic}", "source": "Dawn", "image_url": "x", "topics": [topic],
            "importance": importance}


ROWS = sorted([
    _row(1, "cricket", 0.9), _row(2, "cricket", 0.8), _row(3, "cricket", 0.7),
    _row(4, "ai", 0.85), _row(5, "ai", 0.6),
    _row(6, "economy", 0.95), _row(7, "health", 0.5), _row(8, "world", 0.88), _row(9, "football", 0.3),
], key=lambda r: -r["importance"])


def test_chosen_topics_first_round_robin_then_discovery():
    picks = _pick(ROWS, ["cricket", "ai"], per_topic=2, extra=3)
    assert [p["topic"] for p in picks[:4]] == ["cricket", "ai", "cricket", "ai"]  # every topic shows up early
    assert all(not p["discovery"] for p in picks[:4])
    disc = picks[4:]
    assert [p["topic"] for p in disc] == ["economy", "world", "health"]  # most important other topics
    assert all(p["discovery"] for p in disc)


def test_no_duplicates_and_missing_topics_are_skipped():
    picks = _pick(ROWS, ["cricket", "motorsport"], per_topic=3, extra=0)
    assert [p["id"] for p in picks] == [1, 2, 3]
    assert len({p["id"] for p in picks}) == len(picks)


def test_without_topics_it_is_one_per_topic():
    picks = _pick(ROWS, [], per_topic=0, extra=5)
    assert len({p["topic"] for p in picks}) == len(picks) == 5


def test_same_story_detects_differently_worded_duplicates():
    from app.parhlo.profile import same_story
    assert same_story("Pakistan school roof collapse kills at least 34 children and teacher",
                      "At least 33 pupils and teacher killed after school roof collapse")
    assert not same_story("Petrol price cut by Rs3.93", "Pakistan school roof collapse kills 34")
