import time
from typing import Any

import faiss
import pytest
from sentence_transformers import CrossEncoder, SentenceTransformer


@pytest.mark.integration
def test_creation_query_surfaces_genesis(
    pipeline: tuple[faiss.Index, list[dict[str, Any]], SentenceTransformer, CrossEncoder],
) -> None:
    """Creation query returns at least one Genesis verse."""
    from rag.retrieve import search

    index, mapping, embed_model, cross_encoder = pipeline
    results = search(
        "Dieu créa le ciel et la terre",
        index,
        mapping,
        embed_model,
        cross_encoder,
    )

    assert len(results) == 5
    books = [r["book_title"] for r in results]
    assert "La Genèse" in books


@pytest.mark.integration
def test_forgiveness_query_multiple_books(
    pipeline: tuple[faiss.Index, list[dict[str, Any]], SentenceTransformer, CrossEncoder],
) -> None:
    """Forgiveness query returns verses from multiple books."""
    from rag.retrieve import search

    index, mapping, embed_model, cross_encoder = pipeline
    results = search(
        "le pardon et la miséricorde",
        index,
        mapping,
        embed_model,
        cross_encoder,
    )

    assert len(results) == 5
    books = set(r["book_title"] for r in results)
    assert len(books) >= 2


@pytest.mark.integration
def test_all_scores_in_range(
    pipeline: tuple[faiss.Index, list[dict[str, Any]], SentenceTransformer, CrossEncoder],
) -> None:
    """All result scores are between 0.0 and 1.0."""
    from rag.retrieve import search

    index, mapping, embed_model, cross_encoder = pipeline

    queries = [
        "création du monde",
        "le pardon et la miséricorde",
        "la résurrection des morts",
        "aimer son prochain",
    ]
    for query in queries:
        results = search(query, index, mapping, embed_model, cross_encoder)
        for r in results:
            assert 0.0 <= r["score"] <= 1.0, f"Score {r['score']} out of range for '{query}'"


@pytest.mark.integration
def test_search_time_under_2_seconds(
    pipeline: tuple[faiss.Index, list[dict[str, Any]], SentenceTransformer, CrossEncoder],
) -> None:
    """Each search completes in under 2 seconds."""
    from rag.retrieve import search

    index, mapping, embed_model, cross_encoder = pipeline

    queries = [
        "création du monde",
        "le pardon et la miséricorde",
        "la résurrection des morts",
        "aimer son prochain",
    ]
    for query in queries:
        start = time.time()
        search(query, index, mapping, embed_model, cross_encoder)
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Search for '{query}' took {elapsed:.2f}s"
