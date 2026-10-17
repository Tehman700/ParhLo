"""Files, RAG, ML and vision endpoints."""

import io

from PIL import Image

from app.services.llm import LLMReply
from app.services.rag.chunking import chunk_text


def test_chunking_overlaps_and_covers_text():
    text = " ".join(f"Sentence number {i}." for i in range(400))
    chunks = chunk_text(text, chunk_size=500, overlap=100)
    assert len(chunks) > 5
    assert all(len(c) <= 500 for c in chunks)
    assert "Sentence number 399." in chunks[-1]


def test_upload_csv_is_profiled(client):
    csv = b"a,b,label\n1,2,x\n3,,y\n5,6,x\n"
    r = client.post("/api/files/upload", files=[("files", ("my data.csv", csv, "text/csv"))])
    info = r.json()[0]
    assert info["kind"] == "csv" and info["name"].startswith("my_data_")
    assert info["processing"]["rows"] == 3 and info["processing"]["missing"]["b"] == 1
    names = [f["name"] for f in client.get("/api/files").json()]
    assert info["name"] in names
    assert client.delete(f"/api/files/{info['name']}").status_code == 200


def test_rag_upload_search_and_answer(client, fake_llm):
    doc = (
        "Refund policy. Customers can request a full refund within 14 days of purchase.\n\n"
        "Shipping. Orders ship within 2 business days from the Lahore warehouse.\n\n"
        "Warranty. All laptops include a 1 year hardware warranty."
    )
    r = client.post("/api/files/upload", files=[("files", ("policy.txt", doc.encode(), "text/plain"))])
    proc = r.json()[0]["processing"]
    assert proc["indexed"] and proc["chunks"] >= 1

    hits = client.post("/api/rag/search", json={"question": "how many days for a refund", "top_k": 2}).json()
    assert hits and "refund" in hits[0]["text"].lower() and hits[0]["source"] == r.json()[0]["name"]

    fake = fake_llm(LLMReply(content="Within 14 days [1].", model="fake"))
    ans = client.post("/api/rag/query", json={"question": "refund window?"}).json()
    assert ans["answer"] == "Within 14 days [1]." and ans["sources"]
    assert "14 days" in fake.calls[0]["messages"][0]["content"]  # context was injected

    docs = client.get("/api/rag/documents").json()
    assert any(d["source"].startswith("policy_") for d in docs)


def test_rag_index_existing_upload(client):
    r = client.post("/api/rag/index/handbook.md")
    assert r.status_code == 200 and r.json()["chunks"] >= 1
    hits = client.post("/api/rag/search", json={"question": "annual leave days"}).json()
    assert "20 days" in hits[0]["text"]


def test_ml_classification_train_and_predict(client):
    assert any(d["name"] == "churn.csv" for d in client.get("/api/ml/datasets").json())
    meta = client.post("/api/ml/train", json={
        "filename": "churn.csv", "target": "churn", "model_name": "churn_test",
    }).json()
    assert meta["task"] == "classification"
    assert "customer_id" in meta["dropped_columns"]
    assert meta["metrics"]["accuracy"] > 0.6
    assert meta["feature_importance"]

    pred = client.post("/api/ml/predict", json={"model_name": "churn_test", "records": [
        {"tenure_months": 2, "contract": "Month-to-month", "support_calls": 6},
        {"tenure_months": 70, "contract": "Two year"},  # missing columns get imputed
    ]}).json()
    assert len(pred["predictions"]) == 2 and set(pred["probabilities"][0]) == {"No", "Yes"}
    assert any(m["name"] == "churn_test" for m in client.get("/api/ml/models").json())


def test_ml_regression(client):
    meta = client.post("/api/ml/train", json={
        "filename": "houses.csv", "target": "price", "algorithm": "linear", "model_name": "houses",
    }).json()
    assert meta["task"] == "regression" and meta["metrics"]["r2"] > 0.8


def test_ml_bad_target_is_400(client):
    r = client.post("/api/ml/train", json={"filename": "sales.csv", "target": "nope"})
    assert r.status_code == 400


def test_ml_missing_file_is_404(client):
    r = client.post("/api/ml/profile", json={"filename": "../../secrets.csv"})
    assert r.status_code == 404


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (2400, 1200), "red").save(buf, format="PNG")
    return buf.getvalue()


def test_vision_analyze_with_fake_llm(client, fake_llm):
    fake = fake_llm(LLMReply(content='{"summary": "A red rectangle", "objects": [], "text": "", "tags": ["red"]}', model="fake-vision"))
    r = client.post("/api/vision/analyze", files={"file": ("x.png", _png(), "image/png")}, data={"prompt": "What is this?"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["data"]["summary"] == "A red rectangle"
    assert data["image"]["width"] == 2400 and data["image"]["processed_width"] == 1024
    content = fake.calls[0]["messages"][0]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_vision_without_key_is_503(client):
    r = client.post("/api/vision/analyze", data={"filename": "image.png"})
    assert r.status_code == 503
