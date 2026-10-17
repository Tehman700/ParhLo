from fastapi import APIRouter, Depends

from app.models.schemas import RagQueryRequest
from app.services.llm import LLMService, get_llm
from app.services.rag import IngestResult, RagAnswer, SearchHit, get_rag
from app.utils.files import resolve_data_file

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/documents")
def documents():
    return get_rag().store.list_documents()


@router.post("/index/{filename}", response_model=IngestResult)
async def index_file(filename: str):
    """Index an already-uploaded PDF/TXT/MD file."""
    return await get_rag().ingest_file(resolve_data_file(filename))


@router.post("/search", response_model=list[SearchHit])
async def search(req: RagQueryRequest):
    """Retrieval only — no LLM needed."""
    return await get_rag().search(req.question, req.top_k)


@router.post("/query", response_model=RagAnswer)
async def query(req: RagQueryRequest, llm: LLMService = Depends(get_llm)):
    """Retrieve relevant chunks and generate an answer with numbered source references."""
    return await get_rag().answer(req.question, llm, req.top_k)


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    return {"removed_chunks": get_rag().store.delete_document(doc_id)}


@router.delete("/index")
def clear_index():
    get_rag().store.clear()
    return {"cleared": True}
