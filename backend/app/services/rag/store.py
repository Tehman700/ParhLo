"""A tiny persistent vector store (numpy + JSON). Fine for thousands of chunks.

Swap for FAISS/Chroma later by keeping the same add/search/list_documents/delete_document API.
"""

import json
import threading
from pathlib import Path

import numpy as np

from app.core.errors import AppError


class VectorStore:
    def __init__(self, directory: Path, embedder_name: str):
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self.embedder_name = embedder_name
        self._lock = threading.Lock()
        self.chunks: list[dict] = []
        self.vectors: np.ndarray | None = None
        self._load()

    @property
    def _meta_path(self) -> Path:
        return self.dir / "chunks.json"

    @property
    def _vec_path(self) -> Path:
        return self.dir / "vectors.npy"

    def _load(self) -> None:
        if not self._meta_path.exists():
            return
        meta = json.loads(self._meta_path.read_text(encoding="utf-8"))
        if meta.get("embedder") != self.embedder_name:
            raise AppError(
                f"Index was built with '{meta.get('embedder')}' but current embedder is "
                f"'{self.embedder_name}'. Call DELETE /api/rag/index and re-upload documents.",
                409,
            )
        self.chunks = meta["chunks"]
        self.vectors = np.load(self._vec_path) if self._vec_path.exists() and self.chunks else None

    def _save(self) -> None:
        self._meta_path.write_text(
            json.dumps({"embedder": self.embedder_name, "chunks": self.chunks}), encoding="utf-8"
        )
        if self.vectors is not None:
            np.save(self._vec_path, self.vectors)
        elif self._vec_path.exists():
            self._vec_path.unlink()

    def add(self, chunks: list[dict], vectors: np.ndarray) -> None:
        with self._lock:
            self.chunks.extend(chunks)
            self.vectors = vectors if self.vectors is None else np.vstack([self.vectors, vectors])
            self._save()

    def search(self, query_vector: np.ndarray, top_k: int = 4) -> list[tuple[dict, float]]:
        if self.vectors is None or not self.chunks:
            return []
        scores = self.vectors @ query_vector.reshape(-1)
        idx = np.argsort(-scores)[:top_k]
        return [(self.chunks[i], float(scores[i])) for i in idx]

    def list_documents(self) -> list[dict]:
        docs: dict[str, dict] = {}
        for c in self.chunks:
            d = docs.setdefault(c["doc_id"], {"doc_id": c["doc_id"], "source": c["source"], "chunks": 0})
            d["chunks"] += 1
        return list(docs.values())

    def delete_document(self, doc_id: str) -> int:
        with self._lock:
            keep = [i for i, c in enumerate(self.chunks) if c["doc_id"] != doc_id]
            removed = len(self.chunks) - len(keep)
            self.chunks = [self.chunks[i] for i in keep]
            self.vectors = self.vectors[keep] if self.vectors is not None and keep else None
            self._save()
            return removed

    def clear(self) -> None:
        with self._lock:
            self.chunks, self.vectors = [], None
            self._save()
