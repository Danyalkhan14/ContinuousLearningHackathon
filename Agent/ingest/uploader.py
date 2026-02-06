"""
Embed text chunks and upsert them into a Qdrant collection.

Uses OpenAI's text-embedding-3-large (3072 dimensions) via the
Embeddings API: https://platform.openai.com/docs/api-reference/embeddings
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from config import Settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 10  # chunks per request (kept small for Akash nginx body size limits)


def _ensure_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int,
) -> None:
    """Create the collection if it does not already exist."""
    collections = [c.name for c in client.get_collections().collections]
    if collection_name not in collections:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection '%s' (%d dims)", collection_name, vector_size)
    else:
        logger.info("Collection '%s' already exists", collection_name)


def _embed_batch(
    openai_client: OpenAI,
    texts: list[str],
    model: str,
    dimensions: int,
) -> list[list[float]]:
    """Call OpenAI Embeddings API for a batch of texts."""
    response = openai_client.embeddings.create(
        input=texts,
        model=model,
        dimensions=dimensions,
    )
    return [item.embedding for item in response.data]


def upload_chunks(
    chunks: list[dict[str, Any]],
    settings: Settings,
) -> int:
    """
    Embed all chunks and upsert into Qdrant.

    Returns the number of points upserted.
    """
    openai_client = OpenAI(api_key=settings.openai_api_key)
    qdrant_client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=60,
    )

    _ensure_collection(
        qdrant_client,
        settings.qdrant_collection_name,
        settings.embedding_dimensions,
    )

    total_upserted = 0

    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start : batch_start + BATCH_SIZE]
        texts = [c["text"] for c in batch]

        embeddings = _embed_batch(
            openai_client,
            texts,
            settings.embedding_model,
            settings.embedding_dimensions,
        )

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=emb,
                payload={
                    "text": chunk["text"],
                    **chunk["metadata"],
                },
            )
            for chunk, emb in zip(batch, embeddings)
        ]

        qdrant_client.upsert(
            collection_name=settings.qdrant_collection_name,
            points=points,
        )
        total_upserted += len(points)
        logger.info(
            "Upserted batch %d–%d (%d points)",
            batch_start,
            batch_start + len(points),
            total_upserted,
        )

    logger.info("Upload complete: %d total points in '%s'", total_upserted, settings.qdrant_collection_name)
    return total_upserted
