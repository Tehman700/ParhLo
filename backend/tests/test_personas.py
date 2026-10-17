"""Public sample readers (personas) are read-only: edits are refused and reading events are ignored."""

from fastapi.testclient import TestClient

from app.main import app
from app.parhlo.auth import current_user

PERSONA = {"id": "00000000-0000-0000-0000-000000000001", "name": "Ayesha", "is_demo": True, "persona": True, "onboarded": True}


def test_persona_is_read_only():
    app.dependency_overrides[current_user] = lambda: PERSONA
    try:
        with TestClient(app) as c:
            for method, path, body in [
                ("PATCH", "/api/me", {"city": "Karachi"}),
                ("PUT", "/api/me/topics/cricket", {"on": False}),
                ("POST", "/api/me/following", {"name": "Nvidia"}),
                ("DELETE", "/api/me/following?name=OpenAI", None),
                ("DELETE", "/api/me", None),
                ("DELETE", "/api/me/anchors/1", None),
                ("POST", "/api/learn", None),
                ("POST", "/api/onboarding", {"name": "X", "topics": ["ai"]}),
                ("POST", "/api/editions/generate", {"force": True}),
            ]:
                r = c.request(method, path, json=body)
                assert r.status_code == 403, (method, path, r.status_code)
                assert "sample reader" in r.json()["detail"]
            r = c.post("/api/events", json=[{"type": "like", "article_id": 1}])
            assert r.status_code == 200 and r.json() == {"recorded": 0, "read_only": True}
    finally:
        app.dependency_overrides.clear()
