"""Interest-change reprints: the n8n event is signed, so only the backend can mint a valid one."""

import pytest

from app.parhlo import refresh
from app.parhlo.auth import AuthError


def test_token_binds_user_and_change_time():
    t = refresh._token("u1", 1000)
    assert t == refresh._token("u1", 1000)
    assert t != refresh._token("u2", 1000) and t != refresh._token("u1", 1001)


def test_forged_event_is_rejected():
    ev = refresh.RefreshEvent(user_id="u1", changed_ms=1000, token="0" * 64)
    with pytest.raises(AuthError):
        refresh.check(ev)


def test_internal_endpoints_reject_forged_events():
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app) as c:
        for path in ("/api/internal/paper/check", "/api/internal/paper/refresh"):
            r = c.post(path, json={"user_id": "u1", "changed_ms": 1, "token": "nope"})
            assert r.status_code == 401, (path, r.status_code)
