"""Two-stage retrieval: FAISS vector search + cross-encoder reranking."""

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer

import config
from rag.embeddings import load_cross_encoder, load_embedding_model


def normalize_scores(raw_scores: np.ndarray) -> np.ndarray:
    """Normalize raw cross-encoder scores to [0, 1] using sigmoid.

    Parameters
    ----------
    raw_scores : np.ndarray
        Raw scores from the cross-encoder.

    Returns
    -------
    np.ndarray
        Scores mapped to [0, 1] via sigmoid.
    """
    return 1.0 / (1.0 + np.exp(-raw_scores))  # type: ignore[no-any-return]


def load_pipeline(
    index_path: Path | None = None,
    mapping_path: Path | None = None,
) -> tuple[faiss.Index, list[dict[str, Any]], SentenceTransformer, CrossEncoder]:
    """Load all retrieval components.

    Parameters
    ----------
    index_path : Path or None
        Path to FAISS index file. Defaults to ``config.INDEX_PATH``.
    mapping_path : Path or None
        Path to JSON mapping file. Defaults to ``config.MAPPING_PATH``.

    Returns
    -------
    tuple
        (index, mapping, embed_model, cross_encoder).
    """
    idx_path = index_path or config.INDEX_PATH
    map_path = mapping_path or config.MAPPING_PATH

    index = faiss.read_index(str(idx_path))
    with open(map_path, encoding="utf-8") as f:
        mapping: list[dict[str, Any]] = json.load(f)

    embed_model = load_embedding_model()
    cross_encoder = load_cross_encoder()

    return index, mapping, embed_model, cross_encoder


def search(
    query: str,
    index: faiss.Index,
    mapping: list[dict[str, Any]],
    embed_model: SentenceTransformer,
    cross_encoder: CrossEncoder,
    faiss_top_k: int = config.FAISS_TOP_K,
    rerank_top_k: int = config.RERANK_TOP_K,
) -> list[dict[str, Any]]:
    """Run two-stage retrieval: FAISS search then cross-encoder reranking.

    Parameters
    ----------
    query : str
        Search query string.
    index : faiss.Index
        FAISS inner-product index.
    mapping : list[dict[str, Any]]
        Verse metadata mapping.
    embed_model : SentenceTransformer
        Embedding model for query encoding.
    cross_encoder : CrossEncoder
        Cross-encoder for reranking.
    faiss_top_k : int
        Number of candidates to retrieve from FAISS.
    rerank_top_k : int
        Number of results to return after reranking.

    Returns
    -------
    list[dict[str, Any]]
        Top results sorted by normalized score, each with book_title,
        chapter, verse, text, and score.
    """
    prefixed_query = config.QUERY_PREFIX + query
    query_clean = prefixed_query.replace("\n", " ")

    query_embedding: np.ndarray = embed_model.encode(
        [query_clean],
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    _, indices = index.search(query_embedding, faiss_top_k)
    candidate_indices = indices[0]

    candidates = []
    for idx in candidate_indices:
        idx_int = int(idx)
        if 0 <= idx_int < len(mapping):
            entry = mapping[idx_int]
            text_clean = entry["text"].replace("\n", " ")
            candidates.append((idx_int, text_clean, entry))

    pairs = [[query_clean, c[1]] for c in candidates]
    raw_scores: np.ndarray = cross_encoder.predict(pairs)
    normalized = normalize_scores(np.asarray(raw_scores, dtype=np.float32))

    scored = []
    for i, (_, _, entry) in enumerate(candidates):
        scored.append(
            {
                "book_title": entry["book_title"],
                "chapter": entry["chapter"],
                "verse": entry["verse"],
                "text": entry["text"],
                "score": float(normalized[i]),
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:rerank_top_k]
