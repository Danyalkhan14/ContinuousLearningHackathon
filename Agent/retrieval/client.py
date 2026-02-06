"""
Qdrant retrieval client.

Wraps the qdrant-client SDK to provide a clean search interface
for the deep-research agent. Embeds queries with the same OpenAI
embedding model used during ingestion so that vectors are comparable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from config import Settings

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A single chunk returned from Qdrant."""

    text: str
    score: float
    source_file: str
    page_number: int
    metadata: dict[str, Any] = field(default_factory=dict)


class QdrantRetriever:
    """High-level retrieval wrapper over Qdrant."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._openai = OpenAI(api_key=settings.openai_api_key)
        self._qdrant = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=60,
        )
        self._collection = settings.qdrant_collection_name

    # ── public API ──────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 10,
        source_file: Optional[str] = None,
        score_threshold: Optional[float] = None,
    ) -> list[RetrievedChunk]:
        """
        Semantic search over the clinical trial corpus.

        Args:
            query: Natural-language search query.
            top_k: Max number of results to return.
            source_file: Optional filter to restrict results to a specific file.
            score_threshold: Optional minimum similarity score.

        Returns:
            List of RetrievedChunk objects ordered by descending relevance.
        """
        query_vector = self._embed(query)

        query_filter = None
        if source_file:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="source_file",
                        match=MatchValue(value=source_file),
                    )
                ]
            )

        results = self._qdrant.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter,
            score_threshold=score_threshold,
        )

        chunks = []
        for hit in results:
            payload = hit.payload or {}
            chunks.append(
                RetrievedChunk(
                    text=payload.get("text", ""),
                    score=hit.score,
                    source_file=payload.get("source_file", ""),
                    page_number=payload.get("page_number", 0),
                    metadata={
                        k: v
                        for k, v in payload.items()
                        if k not in ("text",)
                    },
                )
            )

        logger.info(
            "Search for '%s' returned %d results (top score: %.3f)",
            query[:80],
            len(chunks),
            chunks[0].score if chunks else 0.0,
        )
        return chunks

    def multi_query_search(
        self,
        queries: list[str],
        top_k_per_query: int = 5,
    ) -> list[RetrievedChunk]:
        """
        Execute multiple queries and return de-duplicated, re-ranked results.

        Used for multi-hop retrieval where the agent decomposes a complex
        question into several sub-queries.
        """
        seen_texts: set[str] = set()
        all_chunks: list[RetrievedChunk] = []

        for q in queries:
            results = self.search(q, top_k=top_k_per_query)
            for chunk in results:
                # Deduplicate by exact text match
                if chunk.text not in seen_texts:
                    seen_texts.add(chunk.text)
                    all_chunks.append(chunk)

        # Re-rank by score descending
        all_chunks.sort(key=lambda c: c.score, reverse=True)
        logger.info(
            "Multi-query search (%d queries) returned %d unique chunks",
            len(queries),
            len(all_chunks),
        )
        return all_chunks

    # ── internals ───────────────────────────────────────────────────────

    def _embed(self, text: str) -> list[float]:
        """Embed a single text using the configured OpenAI model."""
        response = self._openai.embeddings.create(
            input=[text],
            model=self._settings.embedding_model,
            dimensions=self._settings.embedding_dimensions,
        )
        return response.data[0].embedding
