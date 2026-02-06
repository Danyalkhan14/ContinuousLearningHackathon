"""
Text chunking with configurable size and overlap.

Uses LangChain's RecursiveCharacterTextSplitter for intelligent splitting
that tries to keep semantically coherent units together.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Defaults tuned for clinical trial documents
DEFAULT_CHUNK_SIZE = 1000  # characters
DEFAULT_CHUNK_OVERLAP = 200


def chunk_documents(
    documents: list[dict[str, Any]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    """
    Split documents into smaller chunks, preserving metadata.

    Each input document has {"text": ..., "metadata": {...}}.
    Returns chunks with the same structure, plus a "chunk_index" in metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[dict[str, Any]] = []
    for doc in documents:
        text = doc["text"]
        meta = doc["metadata"]
        splits = splitter.split_text(text)
        for idx, chunk_text in enumerate(splits):
            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": {
                        **meta,
                        "chunk_index": idx,
                    },
                }
            )

    logger.info(
        "Chunked %d documents into %d chunks (size=%d, overlap=%d)",
        len(documents),
        len(chunks),
        chunk_size,
        chunk_overlap,
    )
    return chunks
