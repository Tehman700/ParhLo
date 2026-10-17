import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.errors import AppError
from app.models.schemas import ChatRequest, ChatResponse
from app.services.llm import LLMService, get_llm, parse_json

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _messages(req: ChatRequest) -> list[dict]:
    msgs = [m.model_dump() for m in req.messages]
    if req.system:
        msgs.insert(0, {"role": "system", "content": req.system})
    return msgs


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, llm: LLMService = Depends(get_llm)):
    reply = await llm.chat(
        _messages(req), model=req.model, temperature=req.temperature, json_mode=req.json_mode
    )
    data = parse_json(reply.content or "") if req.json_mode else None
    return ChatResponse(reply=reply.content or "", data=data, model=reply.model, usage=reply.usage)


@router.post("/stream")
async def chat_stream(req: ChatRequest, llm: LLMService = Depends(get_llm)):
    """Server-Sent Events: `data: {"delta": "..."}` lines, then `data: {"done": true}`."""
    _ = llm.client  # fail fast with 503 before the stream starts if not configured

    async def events():
        try:
            async for delta in llm.stream(_messages(req), model=req.model):
                yield f"data: {json.dumps({'delta': delta})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except AppError as e:
            yield f"data: {json.dumps({'error': e.message})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
