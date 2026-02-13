"""Central configuration for the RAG Bible pipeline."""

from pathlib import Path

# Paths
DB_PATH: Path = Path(__file__).parent / "bible.db"
DATA_DIR: Path = Path(__file__).parent / "data"
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
