"""A topic switched off on the dashboard (weight 0.05) is never picked, not even as "something new"."""

import numpy as np

from app.parhlo.rank import select_stories


def story(i, w, score=0.5, importance=0.3):
    e = np.zeros(8, dtype=np.float32)
    e[i % 8] = 1.0
    return {"id": i, "topic_weight": w, "match_sim": 0.0, "score": score, "importance": importance,
            "cluster_size": 1, "source": "Dawn", "embedding": e}


def test_switched_off_topics_never_fill_discovery_or_top_ups():
    pool = [story(i, 0.8, score=0.9 - i * 0.01) for i in range(6)]          # liked topics
    pool += [story(100 + i, 0.05, score=0.95) for i in range(6)]            # switched off, high scoring
    pool += [story(200 + i, 0.1, score=0.4) for i in range(4)]              # never chosen, fine for discovery
    picks = select_stories(pool, 8)
    assert not any(p["topic_weight"] <= 0.05 for p in picks)
    assert any(p.get("discovery") for p in picks)


def test_switched_off_topic_is_not_personal_even_if_it_matches_memory():
    pool = [story(i, 0.8, score=0.6) for i in range(5)]
    hot = story(50, 0.05, score=0.99)
    hot["match_sim"] = 0.9                      # matches something the reader once liked
    picks = select_stories(pool + [hot], 6)
    assert 50 not in {p["id"] for p in picks}


def test_every_switched_on_topic_gets_a_story():
    pool = [{**story(i, 0.8, score=0.9 - i * 0.01), "topics": ["motorsport"]} for i in range(8)]
    pool += [{**story(20, 0.8, score=0.3), "topics": ["health"]}]
    picks = select_stories(pool, 6, on_topics=["motorsport", "health"])
    assert any(p["topics"][0] == "health" for p in picks)
    assert sum(p["topics"][0] == "motorsport" for p in picks) >= 1
