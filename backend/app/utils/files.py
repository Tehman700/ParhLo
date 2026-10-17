"""File helpers: safe names, type detection, locating data files."""

import json
import re
import uuid
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.errors import NotFoundError

TEXT_EXT = {".txt", ".md"}
PDF_EXT = {".pdf"}
TABLE_EXT = {".csv"}
JSON_EXT = {".json"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def file_kind(name: str) -> str:
    ext = Path(name).suffix.lower()
    if ext in TABLE_EXT:
        return "csv"
    if ext in PDF_EXT:
        return "pdf"
    if ext in TEXT_EXT:
        return "text"
    if ext in JSON_EXT:
        return "json"
    if ext in IMAGE_EXT:
        return "image"
    return "other"


def safe_filename(name: str) -> str:
    """Strip directories and odd characters; add a short id to avoid collisions."""
    base = Path(name).name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(base).stem).strip("._") or "file"
    return f"{stem[:60]}_{uuid.uuid4().hex[:6]}{Path(base).suffix.lower()}"


def resolve_data_file(name: str) -> Path:
    """Find an uploaded file by name. Rejects path traversal."""
    clean = Path(name).name
    candidate = get_settings().uploads_dir / clean
    if candidate.is_file():
        return candidate
    raise NotFoundError(f"File '{clean}' not found in uploads")


def to_jsonable(obj: Any) -> Any:
    """Convert numpy/pandas values (incl. NaN) into plain JSON types."""
    return json.loads(json.dumps(obj, default=_default), parse_constant=lambda _: None)


def _default(o: Any):
    if hasattr(o, "item"):
        return o.item()
    if hasattr(o, "tolist"):
        return o.tolist()
    if hasattr(o, "isoformat"):
        return o.isoformat()
    return str(o)
