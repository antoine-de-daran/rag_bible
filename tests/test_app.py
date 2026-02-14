"""Tests for the FastAPI web application."""

import pytest
from fastapi.testclient import TestClient

from app import get_score_label

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
        response = client.post("/search", data={"query": "amour de Dieu"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_results_contain_verse_reference(self, client: TestClient) -> None:
        response = client.post("/search", data={"query": "amour de Dieu"})
        text = response.text
        assert "Jean" in text
        assert "3:16" in text

    def test_results_contain_score_label(self, client: TestClient) -> None:
        response = client.post("/search", data={"query": "amour de Dieu"})
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

    def test_all_low_scores_returns_no_results(self, mock_pipeline_low_scores: None) -> None:
        from app import app as fastapi_app

        low_client = TestClient(fastapi_app)
        response = low_client.post("/search", data={"query": "test query"})
        assert response.status_code == 200
        assert "Aucun verset pertinent" in response.text

    def test_truncates_long_query(self, client: TestClient) -> None:
        long_query = "a" * 500
        response = client.post("/search", data={"query": long_query})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


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


# -- Integration test --


@pytest.mark.integration
def test_search_integration_real_pipeline() -> None:
    """End-to-end test with real models and FAISS index."""
    from app import app as fastapi_app

    with TestClient(fastapi_app) as real_client:
        response = real_client.post("/search", data={"query": "amour de Dieu"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<article" in response.text
