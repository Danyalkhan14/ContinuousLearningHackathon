import os

from dotenv import load_dotenv

load_dotenv()

YOU_API_KEY = os.getenv("YOU_API_KEY", "")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_URL = os.getenv("QDRANT_URL")  # if set, overrides host/port
QDRANT_IN_MEMORY = os.getenv("QDRANT_IN_MEMORY", "false").lower() in ("1", "true", "yes")

COLLECTION_NAME = "documents"
# Local embedding model (sentence-transformers)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# Allowed extensions for upload (CSV and text-like)
ALLOWED_EXTENSIONS = {".csv", ".txt", ".md", ".json", ".xml"}
