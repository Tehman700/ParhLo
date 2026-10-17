"""Morning email: rendering (escaped, complete), unsubscribe tokens, and who gets queued."""

from datetime import date

from app.parhlo import digest

USER = {"id": "11111111-1111-1111-1111-111111111111", "name": "Hina", "email": "hina@example.com", "is_demo": False, "email_morning": True}
PAPER = {
    "number": 4, "lead_id": 1, "reader": {"name": "Hina", "city": "Lahore"},
    "editor_note": "Fuel gets cheaper while cricket heats up.",
    "morning": {"city": "Lahore", "weather": {"temp": 28, "condition": "Clear sky"}, "air": {"aqi": 147, "label": "Unhealthy for sensitive groups"},
                "rates": {"pkr": {"USD": 277.4}}},
    "three_things": [{"text": "Petrol is Rs3.93 cheaper.", "story_id": 1}],
    "stories": [
        {"id": 1, "headline": "Petrol <b>price</b> cut by Rs3.93", "summary": "The government cut prices.", "topics": ["economy"],
         "source": "Dawn", "why": "Because you follow the economy", "image": None, "core": True},
        {"id": 2, "headline": "Pakistan win in Lahore", "summary": "A six-wicket win.", "topics": ["cricket"], "source": "Geo News",
         "why": "Ali liked this", "friend": "Ali"},
    ],
}


def test_render_is_complete_and_escaped():
    subject, body, text = digest.render(USER, PAPER, date(2026, 10, 18))
    assert subject == "Your paper: Petrol <b>price</b> cut by Rs3.93"
    assert "Petrol &lt;b&gt;price&lt;/b&gt;" in body and "<b>price</b>" not in body   # headlines can't inject HTML
    assert "/paper/2026-10-18#story-1" in body and "/pdf/2026-10-18" in body
    assert "28° Clear sky in Lahore" in body and "$1 = Rs 277" in body
    assert "From Ali" in body and "3 things to remember" in body
    assert digest.unsubscribe_url(USER["id"]) in body and digest.unsubscribe_url(USER["id"]) in text
    assert "Sunday, 18 October 2026" in body


def test_unsubscribe_token_is_per_user_and_checked():
    t = digest.unsubscribe_token(USER["id"])
    assert len(t) == 32 and t != digest.unsubscribe_token("22222222-2222-2222-2222-222222222222")
    assert digest.unsubscribe(USER["id"], "wrong") is False


class Conn:
    def __init__(self):
        self.calls = 0

    def execute(self, sql, params=None):
        self.calls += 1
        return type("R", (), {"fetchone": lambda _: {"id": 7}})()


def test_enqueue_only_for_real_readers_who_want_it():
    for user in ({**USER, "is_demo": True}, {**USER, "email": None}, {**USER, "email_morning": False}):
        c = Conn()
        assert digest.enqueue(c, user, 5) is None and c.calls == 0
    c = Conn()
    assert digest.enqueue(c, USER, 5) == 7 and c.calls == 1
    assert digest.enqueue(Conn(), {**USER, "email_morning": False}, 5, kind="manual") == 7  # "send me now" still works
