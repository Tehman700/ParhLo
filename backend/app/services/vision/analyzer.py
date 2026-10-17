"""Image preprocessing (Pillow) + analysis with any vision-capable chat model."""

import base64
import io

from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.llm import LLMService, parse_json

DEFAULT_PROMPT = "Describe this image in detail."
STRUCTURED_INSTRUCTION = (
    "Return a single JSON object with keys: "
    '"summary" (string), "objects" (list of strings), "text" (any visible text, string), '
    '"tags" (list of strings), "details" (object with any task-specific findings).'
)


class ImageInfo(BaseModel):
    width: int
    height: int
    format: str | None
    mode: str
    processed_width: int
    processed_height: int


class VisionResult(BaseModel):
    image: ImageInfo
    model: str
    prompt: str
    text: str | None = None
    data: dict | None = Field(default=None, description="Parsed JSON when structured=True")


def preprocess(raw: bytes, max_side: int = 1024) -> tuple[str, ImageInfo]:
    """Fix orientation, convert to RGB, downscale, and return a base64 JPEG data URL."""
    img = Image.open(io.BytesIO(raw))
    fmt, width, height, mode = img.format, img.width, img.height, img.mode
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    info = ImageInfo(
        width=width, height=height, format=fmt, mode=mode,
        processed_width=img.width, processed_height=img.height,
    )
    return data_url, info


async def analyze_image(
    llm: LLMService, raw: bytes, prompt: str = DEFAULT_PROMPT, structured: bool = True
) -> VisionResult:
    data_url, info = preprocess(raw)
    text_prompt = f"{prompt}\n\n{STRUCTURED_INSTRUCTION}" if structured else prompt
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": text_prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ],
    }]
    model = get_settings().llm_vision_model or get_settings().llm_model
    reply = await llm.chat(messages, model=model, json_mode=structured)
    result = VisionResult(image=info, model=reply.model or model, prompt=prompt, text=reply.content)
    if structured:
        result.data = parse_json(reply.content or "")
    return result
