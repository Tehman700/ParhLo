"""Text extraction. Add new formats (docx, html...) by extending extract_pages()."""

import json
from pathlib import Path

from pypdf import PdfReader


def extract_pages(path: Path) -> list[tuple[int, str]]:
    """Return [(page_number, text)]. Non-paged formats are a single page 1."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        reader = PdfReader(str(path))
        return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    if ext in {".txt", ".md", ".csv"}:
        return [(1, path.read_text(encoding="utf-8", errors="ignore"))]
    if ext == ".json":
        return [(1, json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2))]
    raise ValueError(f"Unsupported document type: {ext}")
