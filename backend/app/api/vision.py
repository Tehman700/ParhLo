from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.errors import AppError
from app.services.llm import LLMService, get_llm
from app.services.vision.analyzer import DEFAULT_PROMPT, VisionResult, analyze_image
from app.utils.files import resolve_data_file

router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.post("/analyze", response_model=VisionResult)
async def analyze(
    file: UploadFile | None = File(None),
    filename: str | None = Form(None, description="Analyze an already-uploaded image instead"),
    prompt: str = Form(DEFAULT_PROMPT),
    structured: bool = Form(True),
    llm: LLMService = Depends(get_llm),
):
    """Send an image to the vision model. Upload `file`, or pass `filename` of an existing upload."""
    if file is not None:
        raw = await file.read()
    elif filename:
        raw = resolve_data_file(filename).read_bytes()
    else:
        raise AppError("Provide an image `file` or a `filename`", 422)
    return await analyze_image(llm, raw, prompt=prompt, structured=structured)
