"""Embeddings via the AI Gateway (OpenAI text-embedding-3-small, 1536-d, unit-normalized)."""

import numpy as np

from app.core.config import get_settings
from app.parhlo.topics import TOPICS, topic_text
from app.services.llm import get_llm

_topic_matrix: tuple[list[str], np.ndarray] | None = None


async def embed_texts(texts: list[str]) -> np.ndarray:
    llm = get_llm()
    model = get_settings().embedding_model
    out: list[list[float]] = []
    for i in range(0, len(texts), 96):
        batch = [t[:2000] or " " for t in texts[i : i + 96]]
        out += await llm.embed(batch, model=model)
    arr = np.array(out, dtype=np.float32)
    return arr / np.clip(np.linalg.norm(arr, axis=1, keepdims=True), 1e-12, None)


async def topic_matrix() -> tuple[list[str], np.ndarray]:
    """Embeddings of every topic description (computed once per process)."""
    global _topic_matrix
    if _topic_matrix is None:
        slugs = list(TOPICS)
        _topic_matrix = (slugs, await embed_texts([topic_text(s) for s in slugs]))
    return _topic_matrix


async def tag_topics(vectors: np.ndarray, hints: list[list[str]]) -> list[list[str]]:
    """Up to 2 topics per article: best embedding matches above a floor, plus the feed's own hints."""
    slugs, tm = await topic_matrix()
    sims = vectors @ tm.T
    tags: list[list[str]] = []
    for row, hint in zip(sims, hints):
        order = np.argsort(-row)
        best = row[order[0]]
        picked = [slugs[j] for j in order[:2] if row[j] >= 0.25 and row[j] >= best - 0.04]
        tags.append(list(dict.fromkeys([*hint, *picked]))[:3])
    return tags
