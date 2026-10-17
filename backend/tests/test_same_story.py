"""Same event, different outlets: headline overlap must catch what embedding clusters missed (real titles, 2026-10-17)."""

from app.parhlo.rank import same_story

VERSIONS = [
    "Any miscalculation by adversaries will invite response beyond their ‘imagination’",
    "Any miscalculation by adversaries will draw 'response beyond imagination', warns CNSC",
    "Any miscalculation will invite response beyond adversaries’ imagination, says CNSC",
    "Any miscalculation will invite response beyond adversary’s imagination, warns strategic commander",
]


def test_reworded_versions_are_one_story():
    for a in VERSIONS:
        for b in VERSIONS:
            assert same_story(a, b), (a, b)


def test_different_stories_stay_apart():
    assert not same_story(VERSIONS[0], "Petrol price cut by Rs3.93 per litre; diesel unchanged")
    assert not same_story("Pakistan to chair IMF and World Bank governors in 2027", "IMF members urge more support amid war spillovers")
