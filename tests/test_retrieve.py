import numpy as np
import pytest


@pytest.mark.unit
def test_normalize_scores_sigmoid() -> None:
    """Known inputs produce expected sigmoid outputs."""
    from rag.retrieve import normalize_scores

    raw = np.array([0.0, 1.0, -1.0], dtype=np.float32)
    result = normalize_scores(raw)
    expected = 1.0 / (1.0 + np.exp(-raw))
    np.testing.assert_allclose(result, expected, atol=1e-6)


@pytest.mark.unit
def test_normalize_scores_zero_maps_to_half() -> None:
    """Raw score 0.0 maps to normalized 0.5."""
    from rag.retrieve import normalize_scores

    result = normalize_scores(np.array([0.0], dtype=np.float32))
    assert abs(result[0] - 0.5) < 1e-6


@pytest.mark.unit
def test_normalize_scores_large_positive() -> None:
    """Raw score 10.0 maps close to 1.0."""
    from rag.retrieve import normalize_scores

    result = normalize_scores(np.array([10.0], dtype=np.float32))
    assert result[0] > 0.999


@pytest.mark.unit
def test_normalize_scores_large_negative() -> None:
    """Raw score -10.0 maps close to 0.0."""
    from rag.retrieve import normalize_scores

    result = normalize_scores(np.array([-10.0], dtype=np.float32))
    assert result[0] < 0.001


@pytest.mark.integration
def test_search_returns_correct_count() -> None:
    """Search returns exactly RERANK_TOP_K results."""
    from rag.retrieve import load_pipeline, search

    index, mapping, embed_model, cross_encoder = load_pipeline()
    results = search("création du monde", index, mapping, embed_model, cross_encoder)
    assert len(results) == 5


@pytest.mark.integration
def test_search_results_sorted_by_score() -> None:
    """Results are sorted by score in descending order."""
    from rag.retrieve import load_pipeline, search

    index, mapping, embed_model, cross_encoder = load_pipeline()
    results = search("amour de Dieu", index, mapping, embed_model, cross_encoder)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.integration
def test_search_results_have_required_fields() -> None:
    """Each result has all required display fields."""
    from rag.retrieve import load_pipeline, search

    index, mapping, embed_model, cross_encoder = load_pipeline()
    results = search("pardon des péchés", index, mapping, embed_model, cross_encoder)
    required_fields = {"book_title", "chapter", "verse", "text", "score"}
    for result in results:
        assert required_fields <= set(result.keys())


@pytest.mark.integration
def test_search_scores_in_range() -> None:
    """All scores are between 0.0 and 1.0 after normalization."""
    from rag.retrieve import load_pipeline, search

    index, mapping, embed_model, cross_encoder = load_pipeline()
    results = search("la résurrection", index, mapping, embed_model, cross_encoder)
    for result in results:
        assert 0.0 <= result["score"] <= 1.0
