"""Tests run fully offline: a temp data dir, no API key, and a scripted FakeLLM where needed."""

import os
import tempfile

# Must be set before the app (and its cached settings) is imported.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="nascon-test-")
os.environ["LLM_API_KEY"] = ""
os.environ["EMBEDDING_PROVIDER"] = "local"
for flag in ("ENABLE_RAG", "ENABLE_ML", "ENABLE_VISION"):
    os.environ[flag] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.llm import LLMReply, get_llm  # noqa: E402


class FakeLLM:
    """Returns scripted replies in order and records every call."""

    def __init__(self, replies: list[LLMReply]):
        self.replies = list(replies)
        self.calls: list[dict] = []

    async def chat(self, messages, **kwargs):
        self.calls.append({"messages": [dict(m) for m in messages], **kwargs})
        return self.replies.pop(0)

    async def stream(self, messages, **kwargs):
        for word in ["Hello", " ", "world"]:
            yield word

    @property
    def client(self):
        return object()


@pytest.fixture(scope="session", autouse=True)
def test_files():
    """Small synthetic files in the temp uploads dir (no data is kept in the repo)."""
    import numpy as np
    import pandas as pd
    from PIL import Image

    from app.core.config import get_settings

    up = get_settings().uploads_dir
    rng = np.random.default_rng(0)
    n = 400
    tenure = rng.integers(1, 72, n)
    contract = rng.choice(["Month-to-month", "One year", "Two year"], n)
    calls = rng.poisson(2, n)
    logit = -0.5 - 0.05 * tenure + 0.5 * calls + np.where(contract == "Month-to-month", 1.5, -1.0)
    pd.DataFrame({
        "customer_id": [f"C{i}" for i in range(n)], "tenure_months": tenure, "contract": contract,
        "support_calls": calls, "churn": np.where(rng.random(n) < 1 / (1 + np.exp(-logit)), "Yes", "No"),
    }).to_csv(up / "churn.csv", index=False)

    area = rng.integers(500, 4000, 300)
    pd.DataFrame({
        "area_sqft": area, "city": rng.choice(["A", "B"], 300), "price": 40 * area + rng.normal(0, 5000, 300),
    }).to_csv(up / "houses.csv", index=False)

    pd.DataFrame({
        "product": rng.choice(["Laptop", "Monitor", "Mouse", "Keyboard", "Headphones"], 100),
        "revenue": rng.integers(10, 2000, 100),
    }).to_csv(up / "sales.csv", index=False)

    (up / "handbook.md").write_text(
        "## Leave\nEmployees receive 20 days of paid annual leave per year.\n\n"
        "## Expenses\nTravel expenses must be submitted within 30 days with receipts.\n\n"
        "## Security\nPasswords must be at least 14 characters and MFA is mandatory.\n" * 3,
        encoding="utf-8",
    )
    Image.new("RGB", (64, 64), "blue").save(up / "image.png")


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def fake_llm():
    def install(*replies: LLMReply) -> FakeLLM:
        fake = FakeLLM(list(replies))
        app.dependency_overrides[get_llm] = lambda: fake
        return fake

    return install
