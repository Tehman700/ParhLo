from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models.schemas import FileInfo
from app.utils.files import file_kind, safe_filename

router = APIRouter(prefix="/api/files", tags=["files"])
MAX_BYTES = 50 * 1024 * 1024


async def process_file(path: Path, kind: str, index_documents: bool) -> dict | None:
    """Quick per-type processing so the UI can show something useful right after upload."""
    settings = get_settings()
    if kind == "csv":
        from app.services.ml.toolkit import load_csv, profile_dataframe

        p = profile_dataframe(load_csv(path), preview_rows=5)
        return {"type": "table", "rows": p["rows"], "columns": p["columns"], "dtypes": p["dtypes"],
                "missing": p["missing"], "preview": p["preview"]}
    if kind in ("pdf", "text") and settings.enable_rag and index_documents:
        from app.services.rag import get_rag

        result = await get_rag().ingest_file(path)
        return {"type": "document", "indexed": True, **result.model_dump()}
    if kind == "image":
        from PIL import Image

        with Image.open(path) as img:
            return {"type": "image", "width": img.width, "height": img.height, "format": img.format}
    return None


@router.post("/upload", response_model=list[FileInfo])
async def upload(files: list[UploadFile] = File(...), index_documents: bool = Form(True)):
    """Upload one or more files. CSVs are profiled, PDFs/TXT are indexed for RAG, images are inspected."""
    settings = get_settings()
    results: list[FileInfo] = []
    for f in files:
        data = await f.read()
        name = safe_filename(f.filename or "file")
        info = FileInfo(name=name, original_name=f.filename, kind=file_kind(name), size=len(data))
        if len(data) > MAX_BYTES:
            info.error = "File too large (max 50 MB)"
            results.append(info)
            continue
        path = settings.uploads_dir / name
        path.write_bytes(data)
        try:
            info.processing = await process_file(path, info.kind, index_documents)
        except Exception as e:  # keep the upload, report what failed
            info.error = f"Saved, but processing failed: {e}"
        results.append(info)
    return results


@router.get("", response_model=list[FileInfo])
def list_files():
    folder = get_settings().uploads_dir
    return [
        FileInfo(name=p.name, kind=file_kind(p.name), size=p.stat().st_size)
        for p in sorted(folder.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if p.is_file() and not p.name.startswith(".")
    ]


@router.delete("/{name}")
def delete_file(name: str):
    path = get_settings().uploads_dir / Path(name).name
    if not path.is_file():
        raise NotFoundError(f"Upload '{name}' not found")
    path.unlink()
    return {"deleted": path.name}
