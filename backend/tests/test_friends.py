"""Friend picks and reaction-undo logic (no database: db() is faked)."""

from contextlib import contextmanager

from app.parhlo import friends, learn


class FakeConn:
    def __init__(self, friend_rows, liked_rows):
        self.friend_rows, self.liked_rows = friend_rows, liked_rows

    def execute(self, sql, params=None):
        rows = self.friend_rows if "from friendships" in sql else self.liked_rows
        return type("R", (), {"fetchall": lambda _: rows, "fetchone": lambda _: rows[0] if rows else None})()


def fake_db(conn):
    @contextmanager
    def _db():
        yield conn
    return _db


def story(i, score, **kw):
    return {"id": i, "score": score, **kw}


def test_friend_picks_swap_weakest_personal(monkeypatch):
    conn = FakeConn([{"id": "f1", "name": "Ali", "email": None}],
                    [{"article_id": 99, "user_id": "f1", "reaction": "like", "saved": False},
                     {"article_id": 98, "user_id": "f1", "reaction": None, "saved": True}])
    monkeypatch.setattr(friends, "db", fake_db(conn))
    picks = [story(1, 0.9), story(2, 0.5), story(3, 0.4), story(4, 0.8, core=True), story(5, 0.1, discovery=True)]
    pool = picks + [story(99, 0.3), story(98, 0.2)]
    out = friends.add_friend_picks({"id": "me"}, pool, picks)
    ids = [p["id"] for p in out]
    assert len(out) == len(picks)
    assert 99 in ids and 98 in ids
    assert 2 not in ids and 3 not in ids          # the two weakest personal picks were replaced
    assert 4 in ids and 5 in ids                  # core and discovery are never replaced
    by = {p["id"]: p for p in out}
    assert by[99]["friend"] == "Ali" and not by[99]["friend_saved"]
    assert by[98]["friend_saved"]


def test_friend_already_chosen_is_labelled_not_duplicated(monkeypatch):
    conn = FakeConn([{"id": "f1", "name": "Reader", "email": "sara@example.com"}],
                    [{"article_id": 1, "user_id": "f1", "reaction": "like", "saved": False}])
    monkeypatch.setattr(friends, "db", fake_db(conn))
    picks = [story(1, 0.9), story(2, 0.5)]
    out = friends.add_friend_picks({"id": "me"}, picks, picks)
    assert [p["id"] for p in out] == [1, 2]
    assert out[0]["friend"] == "sara"             # falls back to the email name


def test_no_sharing_friends_changes_nothing(monkeypatch):
    monkeypatch.setattr(friends, "db", fake_db(FakeConn([], [])))
    picks = [story(1, 0.9)]
    assert friends.add_friend_picks({"id": "me"}, picks + [story(9, 0.1)], picks) == picks


def test_undone_reactions_stop_counting():
    like = {"type": "like", "value": None}
    assert learn.signal({**like, "has_state": True, "cur_reaction": "like", "cur_saved": False}) == 1.0
    assert learn.signal({**like, "has_state": True, "cur_reaction": None, "cur_saved": False}) == 0.0
    assert learn.signal({**like, "has_state": True, "cur_reaction": "dislike", "cur_saved": False}) == 0.0
    assert learn.signal({**like, "has_state": False}) == 1.0  # events from before article_state
    save = {"type": "save", "value": None, "has_state": True, "cur_reaction": None}
    assert learn.signal({**save, "cur_saved": False}) == 0.0
    assert learn.signal({**save, "cur_saved": True}) == 1.0
