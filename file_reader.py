"""Read CSV and text files into chunks for embedding."""
import csv
import io
from pathlib import Path
from typing import Iterator

from config import ALLOWED_EXTENSIONS, CHUNK_OVERLAP, CHUNK_SIZE


def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def is_allowed(filename: str) -> bool:
    return get_extension(filename) in ALLOWED_EXTENSIONS


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if not text or not text.strip():
        return []
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if not chunk.strip():
            start = end - overlap
            continue
        chunks.append(chunk)
        start = end - overlap
    return chunks


def read_csv_content(content: bytes, filename: str, encoding: str = "utf-8") -> str:
    """Read CSV bytes into a single text representation (header + rows as lines)."""
    try:
        raw = content.decode(encoding, errors="replace")
    except Exception:
        raw = content.decode("latin-1", errors="replace")
    reader = csv.reader(io.StringIO(raw))
    lines = []
    for row in reader:
        lines.append(" | ".join(row))
    return "\n".join(lines)


def read_text_content(content: bytes, filename: str, encoding: str = "utf-8") -> str:
    """Read plain text bytes."""
    try:
        return content.decode(encoding, errors="replace")
    except Exception:
        return content.decode("latin-1", errors="replace")


def read_file_to_text(content: bytes, filename: str) -> str:
    """Dispatch by extension: CSV vs text."""
    ext = get_extension(filename)
    if ext == ".csv":
        return read_csv_content(content, filename)
    return read_text_content(content, filename)


def file_to_chunks(content: bytes, filename: str) -> list[tuple[str, str]]:
    """Return list of (chunk_text, source_info). source_info = filename for payload."""
    if not is_allowed(filename):
        return []
    text = read_file_to_text(content, filename)
    chunks = chunk_text(text)
    return [(c, filename) for c in chunks]
