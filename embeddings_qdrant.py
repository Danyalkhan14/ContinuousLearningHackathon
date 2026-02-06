"""Generate embeddings via sentence-transformers (local) and store in Qdrant."""
import hashlib

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from config import (
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    QDRANT_HOST,
    QDRANT_IN_MEMORY,
    QDRANT_PORT,
    QDRANT_URL,
)


def get_qdrant_client() -> QdrantClient:
    if QDRANT_IN_MEMORY:
        return QdrantClient(":memory:")
    if QDRANT_URL:
        return QdrantClient(url=QDRANT_URL)
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collection(client: QdrantClient, vector_size: int) -> None:
    """Create collection if not exists."""
    try:
        client.get_collection(COLLECTION_NAME)
    except Exception:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def get_embedder() -> SentenceTransformer:
    """Lazy-load the model (can be slow on first call)."""
    return SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(model: SentenceTransformer, texts: list[str]) -> list[list[float]]:
    """Batch embed texts with sentence-transformers."""
    if not texts:
        return []
    return model.encode(texts, convert_to_numpy=True).tolist()


def point_id(chunk: str, filename: str, index: int) -> str:
    """Stable id for upsert."""
    raw = f"{filename}:{index}:{chunk[:200]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def upsert_chunks(
    qdrant: QdrantClient,
    chunks_with_source: list[tuple[str, str]],
    model: SentenceTransformer | None = None,
) -> int:
    """Embed chunks and upsert to Qdrant. Returns number of points upserted."""
    if not chunks_with_source:
        return 0
    if model is None:
        model = get_embedder()
    texts = [c[0] for c in chunks_with_source]
    embeddings = embed_texts(model, texts)
    vector_size = len(embeddings[0]) if embeddings else 384
    ensure_collection(qdrant, vector_size=vector_size)
    points = [
        PointStruct(
            id=point_id(text, source, i),
            vector=emb,
            payload={"text": text, "filename": source, "chunk_index": i},
        )
        for i, ((text, source), emb) in enumerate(zip(chunks_with_source, embeddings))
    ]
    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)
