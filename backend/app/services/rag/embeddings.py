"""Embedders. "local" needs no network or downloads; "api" uses the LLM provider's embedding model.

To use sentence-transformers instead, add a class with the same `name` + `embed()` interface.
"""

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from app.core.config import get_settings
from app.services.llm import get_llm


class LocalEmbedder:
    """Hashed word + bigram features. Lexical (keyword) matching, not semantic, but offline and instant."""

    name = "local-hashing-4096"

    def __init__(self):
        self._vec = HashingVectorizer(
            n_features=4096, ngram_range=(1, 2), alternate_sign=False, norm="l2", stop_words="english"
        )

    async def embed(self, texts: list[str]) -> np.ndarray:
        return self._vec.transform(texts).toarray().astype(np.float32)


class ApiEmbedder:
    def __init__(self, model: str):
        self.model = model
        self.name = f"api:{model}"

    async def embed(self, texts: list[str]) -> np.ndarray:
        llm = get_llm()
        vectors: list[list[float]] = []
        for i in range(0, len(texts), 64):
            vectors += await llm.embed(texts[i : i + 64], model=self.model)
        arr = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        return arr / np.clip(norms, 1e-12, None)


def get_embedder():
    s = get_settings()
    if s.embedding_provider == "api":
        return ApiEmbedder(s.embedding_model)
    return LocalEmbedder()
