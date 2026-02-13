import time

import pytest


@pytest.mark.integration
def test_creation_query_surfaces_genesis() -> None:
    """Creation query returns at least one Genesis verse."""
    from retrieve import load_pipeline, search

    index, mapping, embed_model, cross_encoder = load_pipeline()
    results = search("Dieu créa le ciel et la terre", index, mapping, embed_model, cross_encoder)

    assert len(results) == 5
    books = [r["book_title"] for r in results]
    assert "La Genèse" in books


@pytest.mark.integration
def test_forgiveness_query_multiple_books() -> None:
    """Forgiveness query returns verses from multiple books."""
    from retrieve import load_pipeline, search

    index, mapping, embed_model, cross_encoder = load_pipeline()
    results = search("le pardon et la miséricorde", index, mapping, embed_model, cross_encoder)

    assert len(results) == 5
    books = set(r["book_title"] for r in results)
    assert len(books) >= 2


@pytest.mark.integration
def test_all_scores_in_range() -> None:
    """All result scores are between 0.0 and 1.0."""
    from retrieve import load_pipeline, search

    index, mapping, embed_model, cross_encoder = load_pipeline()

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
def test_search_time_under_2_seconds() -> None:
    """Each search completes in under 2 seconds."""
    from retrieve import load_pipeline, search

    index, mapping, embed_model, cross_encoder = load_pipeline()

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


@pytest.mark.integration
def test_print_sample_results() -> None:
    """Print formatted results for manual review."""
    from retrieve import load_pipeline, search

    index, mapping, embed_model, cross_encoder = load_pipeline()

    queries = [
        "création du monde",
        "le pardon et la miséricorde",
        "la résurrection des morts",
        "aimer son prochain",
    ]
    for query in queries:
        results = search(query, index, mapping, embed_model, cross_encoder)
        print(f"\n{'=' * 80}")
        print(f"Query: {query}")
        print(f"{'=' * 80}")
        for i, r in enumerate(results, 1):
            ref = f"{r['book_title']} {r['chapter']}:{r['verse']}"
            print(f"\n  {i}. [{r['score']:.3f}] {ref}")
            print(f"     {r['text'][:120]}")
