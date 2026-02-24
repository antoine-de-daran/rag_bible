"""Tests for the FastAPI web application."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import get_score_label, get_verse_context, sanitize_query

# -- Sanitize query unit tests --


@pytest.mark.unit
class TestSanitizeQuery:
    def test_strips_script_tag(self) -> None:
        assert sanitize_query('<script>alert("x")</script>hello world') == 'alert("x")hello world'

    def test_strips_nested_tags(self) -> None:
        assert sanitize_query("<div><b>text</b></div>") == "text"

    def test_strips_null_bytes(self) -> None:
        assert sanitize_query("hello\x00world") == "helloworld"

    def test_preserves_plain_text(self) -> None:
        assert sanitize_query("quel est l amour de Dieu") == "quel est l amour de Dieu"

    def test_truncates_to_max_length(self) -> None:
        result = sanitize_query("mot " * 100)
        assert len(result) <= 300

    def test_collapses_whitespace(self) -> None:
        assert sanitize_query("un   deux\t\ntrois") == "un deux trois"


# -- Score label unit tests --


@pytest.mark.unit
class TestGetScoreLabel:
    def test_very_relevant(self) -> None:
        assert get_score_label(0.85) == "Tres pertinent"
        assert get_score_label(0.80) == "Tres pertinent"
        assert get_score_label(1.0) == "Tres pertinent"

    def test_relevant(self) -> None:
        assert get_score_label(0.65) == "Pertinent"
        assert get_score_label(0.50) == "Pertinent"

    def test_low(self) -> None:
        assert get_score_label(0.45) == "Peu pertinent"
        assert get_score_label(0.30) == "Peu pertinent"

    def test_weak(self) -> None:
        assert get_score_label(0.25) == "Faible pertinence"
        assert get_score_label(0.0) == "Faible pertinence"


# -- Endpoint tests (mocked pipeline) --


@pytest.mark.unit
class TestHealthEndpoint:
    def test_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.unit
class TestSearchEndpoint:
    def test_returns_html(self, client: TestClient) -> None:
        response = client.post("/search", data={"query": "quel est l amour de Dieu"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_results_contain_verse_reference(self, client: TestClient) -> None:
        response = client.post("/search", data={"query": "quel est l amour de Dieu"})
        text = response.text
        assert "Jean" in text
        assert "3:16" in text

    def test_results_contain_score_label(self, client: TestClient) -> None:
        response = client.post("/search", data={"query": "quel est l amour de Dieu"})
        text = response.text
        assert "Tres pertinent" in text

    def test_empty_query_returns_error(self, client: TestClient) -> None:
        response = client.post("/search", data={"query": ""})
        assert response.status_code == 200
        assert "Veuillez saisir" in response.text

    def test_whitespace_query_returns_error(self, client: TestClient) -> None:
        response = client.post("/search", data={"query": "   "})
        assert response.status_code == 200
        assert "Veuillez saisir" in response.text

    def test_low_scores_still_shown(self, mock_pipeline_low_scores: None) -> None:
        from app import app as fastapi_app

        low_client = TestClient(fastapi_app)
        response = low_client.post("/search", data={"query": "un deux trois quatre cinq"})
        assert response.status_code == 200
        assert "La Gen" in response.text
        assert "Faible pertinence" in response.text

    def test_truncates_long_query(self, client: TestClient) -> None:
        long_query = "mot " * 100
        response = client.post("/search", data={"query": long_query})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


@pytest.mark.unit
class TestInputValidation:
    def test_single_word_query_accepted(self, client: TestClient) -> None:
        response = client.post("/search", data={"query": "amour"})
        assert response.status_code == 200
        assert "Veuillez saisir" not in response.text


@pytest.mark.unit
class TestErrorHandling:
    def test_runtime_error_returns_error_template(self, client: TestClient) -> None:
        from unittest.mock import patch

        with patch("app._run_search", side_effect=RuntimeError("boom")):
            response = client.post("/search", data={"query": "un deux trois quatre cinq"})
        assert response.status_code == 200
        assert "erreur interne" in response.text

    def test_traceback_not_exposed(self, client: TestClient) -> None:
        from unittest.mock import patch

        with patch("app._run_search", side_effect=RuntimeError("secret_trace")):
            response = client.post("/search", data={"query": "un deux trois quatre cinq"})
        assert "secret_trace" not in response.text
        assert "Traceback" not in response.text


@pytest.mark.unit
class TestCORS:
    def test_cors_headers_present(self, client: TestClient) -> None:
        response = client.options(
            "/search",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert "access-control-allow-origin" in response.headers


# -- Verse context unit tests --


def _make_mapping() -> list[dict[str, Any]]:
    """Build a small mapping for context tests."""
    entries: list[dict[str, Any]] = []
    # Book A: 5 verses
    for i in range(5):
        entries.append(
            {
                "book_id": 1,
                "book_title": "BookA",
                "chapter": "1",
                "verse": str(i + 1),
                "text": f"Verse A {i + 1}",
            }
        )
    # Book B: 3 verses
    for i in range(3):
        entries.append(
            {
                "book_id": 2,
                "book_title": "BookB",
                "chapter": "2",
                "verse": str(i + 1),
                "text": f"Verse B {i + 1}",
            }
        )
    return entries


def _build_index(
    mapping: list[dict[str, Any]],
) -> dict[tuple[str, str, str], int]:
    idx: dict[tuple[str, str, str], int] = {}
    for i, e in enumerate(mapping):
        idx[(e["book_title"], e["chapter"], e["verse"])] = i
    return idx


@pytest.mark.unit
class TestGetVerseContext:
    def test_returns_surrounding_verses(self) -> None:
        mapping = _make_mapping()
        verse_idx = _build_index(mapping)
        result = {"book_title": "BookA", "chapter": "1", "verse": "3", "text": "Verse A 3"}
        ctx = get_verse_context(result, mapping, verse_idx, n=2)
        assert len(ctx) == 5
        verses = [c["verse"] for c in ctx]
        assert verses == ["1", "2", "3", "4", "5"]

    def test_book_bounded_no_cross_book(self) -> None:
        mapping = _make_mapping()
        verse_idx = _build_index(mapping)
        result = {"book_title": "BookA", "chapter": "1", "verse": "5", "text": "Verse A 5"}
        ctx = get_verse_context(result, mapping, verse_idx, n=2)
        for c in ctx:
            assert "BookB" not in c.get("text", "")

    def test_start_of_mapping(self) -> None:
        mapping = _make_mapping()
        verse_idx = _build_index(mapping)
        result = {"book_title": "BookA", "chapter": "1", "verse": "1", "text": "Verse A 1"}
        ctx = get_verse_context(result, mapping, verse_idx, n=2)
        assert ctx[0]["is_match"] is True
        assert len(ctx) == 3

    def test_end_of_mapping(self) -> None:
        mapping = _make_mapping()
        verse_idx = _build_index(mapping)
        result = {"book_title": "BookB", "chapter": "2", "verse": "3", "text": "Verse B 3"}
        ctx = get_verse_context(result, mapping, verse_idx, n=2)
        assert ctx[-1]["is_match"] is True
        assert len(ctx) == 3

    def test_verse_not_in_index_fallback(self) -> None:
        mapping = _make_mapping()
        verse_idx = _build_index(mapping)
        result = {"book_title": "Unknown", "chapter": "99", "verse": "1", "text": "Mystery"}
        ctx = get_verse_context(result, mapping, verse_idx, n=2)
        assert len(ctx) == 1
        assert ctx[0]["is_match"] is True
        assert ctx[0]["text"] == "Mystery"

    def test_exactly_one_match(self) -> None:
        mapping = _make_mapping()
        verse_idx = _build_index(mapping)
        result = {"book_title": "BookA", "chapter": "1", "verse": "3", "text": "Verse A 3"}
        ctx = get_verse_context(result, mapping, verse_idx, n=2)
        matches = [c for c in ctx if c["is_match"]]
        assert len(matches) == 1


# -- Adversarial input tests --


@pytest.mark.unit
class TestAdversarialInput:
    def test_xss_script_tag_stripped(self, client: TestClient) -> None:
        query = '<script>alert("xss")</script> un deux trois quatre cinq'
        response = client.post("/search", data={"query": query})
        assert "<script>" not in response.text

    def test_xss_img_onerror_stripped(self, client: TestClient) -> None:
        query = '<img onerror="alert(1)"> un deux trois quatre cinq'
        response = client.post("/search", data={"query": query})
        assert "<img" not in response.text

    def test_very_long_input_handled(self, client: TestClient) -> None:
        query = "mot " * 10000
        response = client.post("/search", data={"query": query})
        assert response.status_code == 200

    def test_unicode_edge_cases(self, client: TestClient) -> None:
        query = "Dieu est amour \u200b\u00e9\u00e8\u00ea\u00eb cinq mots"
        response = client.post("/search", data={"query": query})
        assert response.status_code == 200

    def test_null_bytes_not_in_response(self, client: TestClient) -> None:
        query = "un\x00deux\x00trois\x00quatre\x00cinq"
        response = client.post("/search", data={"query": query})
        assert "\x00" not in response.text

    def test_sql_injection_harmless(self, client: TestClient) -> None:
        query = "'; DROP TABLE verses; -- un deux trois"
        response = client.post("/search", data={"query": query})
        assert response.status_code == 200

    def test_empty_after_stripping_returns_error(self, client: TestClient) -> None:
        query = "<b></b> <i></i> <div></div>"
        response = client.post("/search", data={"query": query})
        assert "Veuillez saisir" in response.text


# -- Integration test --


@pytest.mark.integration
def test_search_integration_real_pipeline() -> None:
    """End-to-end test with real models and FAISS index."""
    from app import app as fastapi_app

    with TestClient(fastapi_app) as real_client:
        response = real_client.post("/search", data={"query": "quel est l amour de Dieu"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "result-card" in response.text
