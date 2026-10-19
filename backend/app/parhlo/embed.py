"""Embeddings via the AI Gateway (OpenAI text-embedding-3-small, 1536-d, unit-normalized)."""

import numpy as np

from app.core.config import get_settings
from app.parhlo.topics import TOPICS, topic_text
from app.services.llm import get_llm

_topic_matrix: tuple[list[str], np.ndarray] | None = None


# ── INGEST STEP 6 (detail) ── Turn texts into vectors (embeddings): lists of 1536 numbers that capture MEANING.
# Two texts about the same thing ("petrol price cut" / "fuel gets cheaper") get vectors pointing the same way,
# which is how ParhLo matches stories to interests, groups the same event, and searches by meaning.
async def embed_texts(texts: list[str]) -> np.ndarray:
    llm = get_llm()                                  # our OpenAI client (app/services/llm)
    model = get_settings().embedding_model           # "text-embedding-3-small": cheap (~$0.02 per million tokens), good quality
    out: list[list[float]] = []
    # Send 96 texts per API call (batching = far fewer requests); cut each text to 2,000 characters
    # (title + summary is all we need) and never send an empty string (the API rejects it).
    for i in range(0, len(texts), 96):
        batch = [t[:2000] or " " for t in texts[i : i + 96]]
        out += await llm.embed(batch, model=model)
    arr = np.array(out, dtype=np.float32)            # float32: half the memory of float64, plenty of precision
    # Normalise every vector to length 1. Then a plain dot product (a · b) equals cosine similarity,
    # which is what ranking, clustering and search compare (in numpy here, and in pgvector in the database).
    return arr / np.clip(np.linalg.norm(arr, axis=1, keepdims=True), 1e-12, None)


async def topic_matrix() -> tuple[list[str], np.ndarray]:
    """Embeddings of every topic description (computed once per process)."""
    # A small in-memory cache: the 17 topic descriptions are embedded the first time they're needed, then reused
    # for every later call while the server instance stays warm (they never change, so there's no need to recompute).
    global _topic_matrix
    if _topic_matrix is None:
        slugs = list(TOPICS)
        _topic_matrix = (slugs, await embed_texts([topic_text(s) for s in slugs]))
    return _topic_matrix


# ── INGEST STEP 6/7 (fallback) ── Topic tags WITHOUT Jev: compare each article's vector with each topic's vector.
# Used only when Jev is unavailable, so every article still gets sensible topics (graceful degradation).
async def tag_topics(vectors: np.ndarray, hints: list[list[str]]) -> list[list[str]]:
    """Up to 2 topics per article: best embedding matches above a floor, plus the feed's own hints."""
    slugs, tm = await topic_matrix()
    # One matrix multiplication = similarity of EVERY article to EVERY topic at once (rows: articles, cols: topics).
    # Keep up to 2 topics that score ≥ 0.25 and are within 0.04 of the best one; feed hints come first.
    sims = vectors @ tm.T
    tags: list[list[str]] = []
    for row, hint in zip(sims, hints):
        order = np.argsort(-row)
        best = row[order[0]]
        picked = [slugs[j] for j in order[:2] if row[j] >= 0.25 and row[j] >= best - 0.04]
        tags.append(list(dict.fromkeys([*hint, *picked]))[:3])
    return tags
