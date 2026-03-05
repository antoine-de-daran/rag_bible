"""Central configuration for the RAG Bible pipeline."""

import os
import platform
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

# ONNX quantized model file (architecture-specific)
_machine = platform.machine()
_onnx_map: dict[str, str] = {
    "x86_64": "onnx/model_qint8_avx512.onnx",
    "AMD64": "onnx/model_qint8_avx512.onnx",
    "arm64": "onnx/model_qint8_arm64.onnx",
}
ONNX_FILE_NAME: str = _onnx_map.get(_machine, "onnx/model.onnx")

# Retrieval parameters
FAISS_TOP_K: int = 20
RERANK_TOP_K: int = 5

# Ingestion filters
MIN_TEXT_LENGTH: int = 10
MIN_WORD_COUNT: int = 3

# Web serving
_DEFAULT_CORS = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000"
CORS_ORIGINS: list[str] = [
    o.strip() for o in os.environ.get("CORS_ORIGINS", _DEFAULT_CORS).split(",") if o.strip()
]
RELEVANCE_THRESHOLD: float = 0.0
SCORE_LABELS: list[tuple[float, str]] = [
    (0.8, "Très pertinent"),
    (0.5, "Pertinent"),
    (0.3, "Peu pertinent"),
    (0.0, "Non pertinent"),
]
MAX_QUERY_LENGTH: int = 300
CONTEXT_VERSES: int = 2

# Feedback
FEEDBACK_BUFFER_PATH: Path = DATA_DIR / "feedback_buffer.jsonl"
FEEDBACK_HF_REPO: str = os.environ.get("FEEDBACK_HF_REPO", "adedaran/rag-bible-feedback")
FEEDBACK_FLUSH_THRESHOLD: int = 5
FEEDBACK_FLUSH_INTERVAL_S: int = 300  # 5 minutes
