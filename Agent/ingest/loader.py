"""
Multi-format document loader.

Supported formats: PDF (.pdf), Word (.docx), plain text (.txt).
Each loaded document is returned as a list of dicts with keys:
  - text: str
  - metadata: dict (source_file, file_type, page_number)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_pdf(path: Path) -> list[dict[str, Any]]:
    """Load a PDF using PyMuPDF (fitz)."""
    import fitz  # pymupdf

    docs: list[dict[str, Any]] = []
    with fitz.open(str(path)) as pdf:
        for page_num, page in enumerate(pdf, start=1):
            text = page.get_text("text")
            if text.strip():
                docs.append(
                    {
                        "text": text,
                        "metadata": {
                            "source_file": path.name,
                            "file_type": "pdf",
                            "page_number": page_num,
                        },
                    }
                )
    return docs


def _load_docx(path: Path) -> list[dict[str, Any]]:
    """Load a Word document using python-docx."""
    from docx import Document

    doc = Document(str(path))
    full_text = "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    if not full_text.strip():
        return []
    return [
        {
            "text": full_text,
            "metadata": {
                "source_file": path.name,
                "file_type": "docx",
                "page_number": 1,  # DOCX doesn't have native pages
            },
        }
    ]


def _load_txt(path: Path) -> list[dict[str, Any]]:
    """Load a plain text file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return []
    return [
        {
            "text": text,
            "metadata": {
                "source_file": path.name,
                "file_type": "txt",
                "page_number": 1,
            },
        }
    ]


_LOADERS = {
    ".pdf": _load_pdf,
    ".docx": _load_docx,
    ".txt": _load_txt,
}


def load_file(path: Path) -> list[dict[str, Any]]:
    """Load a single file and return a list of page-level documents."""
    suffix = path.suffix.lower()
    loader = _LOADERS.get(suffix)
    if loader is None:
        logger.warning("Unsupported file type %s – skipping %s", suffix, path.name)
        return []
    logger.info("Loading %s (%s)", path.name, suffix)
    return loader(path)


def load_directory(dir_path: Path) -> list[dict[str, Any]]:
    """Recursively load all supported files from a directory."""
    all_docs: list[dict[str, Any]] = []
    for fpath in sorted(dir_path.rglob("*")):
        if fpath.is_file() and fpath.suffix.lower() in _LOADERS:
            all_docs.extend(load_file(fpath))
    logger.info("Loaded %d document segments from %s", len(all_docs), dir_path)
    return all_docs
