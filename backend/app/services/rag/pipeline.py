"""Document QA: ingest -> chunk -> embed -> store -> retrieve -> answer with sources."""

import hashlib
from pathlib import Path

from pydantic import BaseModel

from app.core.config import get_settings
from app.services.llm import LLMService
from app.services.rag.chunking import chunk_text
from app.services.rag.embeddings import get_embedder
from app.services.rag.loaders import extract_pages
from app.services.rag.store import VectorStore

ANSWER_PROMPT = """Answer the question using ONLY the context below.
Cite sources inline like [1], [2] matching the numbered context blocks.
If the answer is not in the context, say you could not find it in the documents.

Context:
{context}

Question: {question}"""


class SearchHit(BaseModel):
    ref: int
    doc_id: str
    source: str
    page: int
    chunk_index: int
    score: float
    text: str


class RagAnswer(BaseModel):
    answer: str
    sources: list[SearchHit]
    model: str = ""


class IngestResult(BaseModel):
    doc_id: str
    source: str
    pages: int
    chunks: int
    characters: int


class RagPipeline:
    def __init__(self, store: VectorStore, embedder, chunk_size: int = 900, overlap: int = 150):
        self.store = store
        self.embedder = embedder
        self.chunk_size = chunk_size
        self.overlap = overlap

    async def ingest_file(self, path: Path, source_name: str | None = None) -> IngestResult:
        source = source_name or path.name
        doc_id = hashlib.sha1(f"{source}:{path.stat().st_size}".encode()).hexdigest()[:12]
        self.store.delete_document(doc_id)  # re-ingest replaces old chunks

        chunks: list[dict] = []
        pages = extract_pages(path)
        for page_no, text in pages:
            for i, piece in enumerate(chunk_text(text, self.chunk_size, self.overlap)):
                chunks.append({
                    "doc_id": doc_id, "source": source, "page": page_no,
                    "chunk_index": i, "text": piece,
                })
        if chunks:
            vectors = await self.embedder.embed([c["text"] for c in chunks])
            self.store.add(chunks, vectors)
        return IngestResult(
            doc_id=doc_id, source=source, pages=len(pages), chunks=len(chunks),
            characters=sum(len(t) for _, t in pages),
        )

    async def search(self, query: str, top_k: int = 4) -> list[SearchHit]:
        qvec = (await self.embedder.embed([query]))[0]
        return [
            SearchHit(ref=i + 1, score=round(score, 4), **{k: c[k] for k in ("doc_id", "source", "page", "chunk_index", "text")})
            for i, (c, score) in enumerate(self.store.search(qvec, top_k))
            if score > 0
        ]

    async def answer(self, question: str, llm: LLMService, top_k: int = 4) -> RagAnswer:
        hits = await self.search(question, top_k)
        if not hits:
            return RagAnswer(answer="No relevant passages found. Upload documents first.", sources=[])
        context = "\n\n".join(f"[{h.ref}] ({h.source}, p.{h.page})\n{h.text}" for h in hits)
        reply = await llm.chat([
            {"role": "user", "content": ANSWER_PROMPT.format(context=context, question=question)}
        ])
        return RagAnswer(answer=reply.content or "", sources=hits, model=reply.model)


_rag: RagPipeline | None = None


def get_rag() -> RagPipeline:
    global _rag
    if _rag is None:
        embedder = get_embedder()
        store = VectorStore(get_settings().processed_dir / "rag_index", embedder.name)
        _rag = RagPipeline(store, embedder)
    return _rag


def reset_rag() -> None:
    """Drop the cached pipeline (used by tests / after config changes)."""
    global _rag
    _rag = None
