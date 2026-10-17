from fastapi import APIRouter

from app.core.config import get_settings
from app.tools import all_tools

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    s = get_settings()
    return {"status": "ok", "llm_configured": s.llm_configured}


@router.get("/api/config")
def config():
    """What the frontend needs to know: which modules are on and which model is used (never the key)."""
    s = get_settings()
    return {
        "app_name": s.app_name,
        "llm": {
            "configured": s.llm_configured,
            "model": s.llm_model,
            "vision_model": s.llm_vision_model or s.llm_model,
            "base_url": s.llm_base_url or "https://api.openai.com/v1",
        },
        "embeddings": s.embedding_provider,
        "features": {"rag": s.enable_rag, "ml": s.enable_ml, "vision": s.enable_vision},
        "tools": [t.name for t in all_tools()],
    }
