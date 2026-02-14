"""Central configuration for the RAG Bible pipeline."""

from pathlib import Path

# Paths
DATA_DIR: Path = Path(__file__).parent / "data"
DB_PATH: Path = DATA_DIR / "bible.db"
INDEX_PATH: Path = DATA_DIR / "index.faiss"
MAPPING_PATH: Path = DATA_DIR / "mapping.json"

# Embedding model
EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSION: int = 384

# Cross-encoder model
CROSS_ENCODER_MODEL: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"

# Retrieval parameters
FAISS_TOP_K: int = 20
RERANK_TOP_K: int = 5

# Ingestion filters
MIN_TEXT_LENGTH: int = 10
MIN_WORD_COUNT: int = 3

# Query prefix (empty for MiniLM, set for bge-m3 later)
QUERY_PREFIX: str = ""

# Web serving
CORS_ORIGINS: list[str] = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
]
RELEVANCE_THRESHOLD: float = 0.5
SCORE_LABELS: list[tuple[float, str]] = [
    (0.8, "Tres pertinent"),
    (0.5, "Pertinent"),
    (0.3, "Peu pertinent"),
    (0.0, "Faible pertinence"),
]
MAX_QUERY_LENGTH: int = 300
