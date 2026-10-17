"""RAG search exposed as an agent tool. Only loaded when ENABLE_RAG=true."""

from typing import Annotated

from pydantic import Field

from app.services.rag.pipeline import get_rag
from app.tools.registry import tool


@tool(description="Search the uploaded/indexed documents and return the most relevant passages with sources.")
async def search_documents(
    query: Annotated[str, Field(description="What to look for")],
    top_k: int = 4,
) -> dict:
    hits = await get_rag().search(query, top_k=top_k)
    return {"results": [h.model_dump() for h in hits]}
