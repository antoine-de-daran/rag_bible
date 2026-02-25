"""Shared test fixtures for the RAG Bible test suite."""

from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sample_verses() -> list[dict[str, Any]]:
    """Representative verse dicts covering edge cases."""
    return [
        {
            "rowid": 1,
            "book": "Gn",
            "book_id": 1,
            "book_title": "La Genèse",
            "chapter": "1",
            "chapter_id": 0,
            "chapter_title": "Chapitre 1",
            "verse": "1",
            "text": "AU COMMENCEMENT,\nDieu créa le ciel et la terre.",
        },
        {
            "rowid": 2,
            "book": "Gn",
            "book_id": 1,
            "book_title": "La Genèse",
            "chapter": "1",
            "chapter_id": 0,
            "chapter_title": "Chapitre 1",
            "verse": "3",
            "text": "Dieu dit :\n« Que la lumière soit. »\nEt la lumière fut.",
        },
        {
            "rowid": 100,
            "book": "Ps",
            "book_id": 192,
            "book_title": "Livre des Psaumes",
            "chapter": "117",
            "chapter_id": 1298,
            "chapter_title": "Psaume 117",
            "verse": "",
            "text": "Alléluia",
        },
        {
            "rowid": 200,
            "book": "Ct",
            "book_id": 25,
            "book_title": "Le Cantique des Cantiques",
            "chapter": "4",
            "chapter_id": 586,
            "chapter_title": "Chapitre 4",
            "verse": "",
            "text": "LUI",
        },
        {
            "rowid": 300,
            "book": "Ct",
            "book_id": 25,
            "book_title": "Le Cantique des Cantiques",
            "chapter": "2",
            "chapter_id": 584,
            "chapter_title": "Chapitre 2",
            "verse": "",
            "text": "ELLE",
        },
        {
            "rowid": 400,
            "book": "Nb",
            "book_id": 4,
            "book_title": "Les Nombres",
            "chapter": "31",
            "chapter_id": 147,
            "chapter_title": "Chapitre 31",
            "verse": "45",
            "text": "30 500 ânes,",
        },
        {
            "rowid": 500,
            "book": "Jn",
            "book_id": 67,
            "book_title": "Évangile selon saint Jean",
            "chapter": "3",
            "chapter_id": 1475,
            "chapter_title": "Chapitre 3",
            "verse": "16",
            "text": (
                "Car Dieu a tellement aimé le monde\n"
                "qu'il a donné son Fils unique,\n"
                "afin que quiconque croit en lui ne se perde pas,\n"
                "mais obtienne la vie éternelle."
            ),
        },
        {
            "rowid": 600,
            "book": "Mt",
            "book_id": 65,
            "book_title": "Évangile selon saint Matthieu",
            "chapter": "6",
            "chapter_id": 1411,
            "chapter_title": "Chapitre 6",
            "verse": "9",
            "text": (
                "Vous donc, priez ainsi :\n"
                "Notre Père, qui es aux cieux,\n"
                "que ton nom soit sanctifié,"
            ),
        },
        {
            "rowid": 700,
            "book": "Rm",
            "book_id": 74,
            "book_title": "Lettre aux Romains",
            "chapter": "8",
            "chapter_id": 1542,
            "chapter_title": "Chapitre 8",
            "verse": "28",
            "text": (
                "Nous le savons, quand les hommes aiment Dieu, "
                "lui-même fait tout contribuer à leur bien, "
                "puisqu'ils sont appelés selon le dessein de son amour."
            ),
        },
        {
            "rowid": 800,
            "book": "Dn",
            "book_id": 34,
            "book_title": "Daniel",
            "chapter": "11",
            "chapter_id": 849,
            "chapter_title": "Chapitre 11",
            "verse": "",
            "text": "[",
        },
    ]


@pytest.fixture
def sample_texts() -> list[str]:
    """Verse text strings for embedding tests."""
    return [
        "AU COMMENCEMENT, Dieu créa le ciel et la terre.",
        "Dieu dit : « Que la lumière soit. » Et la lumière fut.",
        "Car Dieu a tellement aimé le monde qu'il a donné son Fils unique.",
    ]


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Temporary directory for test artifacts."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


def _mock_search_results(relevant: bool = True) -> list[dict[str, Any]]:
    """Build fake search results for testing."""
    if not relevant:
        return [
            {
                "book_title": "La Genèse",
                "chapter": "1",
                "verse": "1",
                "text": "AU COMMENCEMENT, Dieu créa le ciel et la terre.",
                "score": 0.2,
            },
        ]
    return [
        {
            "book_title": "Évangile selon saint Jean",
            "chapter": "3",
            "verse": "16",
            "text": "Car Dieu a tellement aimé le monde\nqu'il a donné son Fils unique.",
            "score": 0.92,
        },
        {
            "book_title": "Lettre aux Romains",
            "chapter": "8",
            "verse": "28",
            "text": "Nous le savons, quand les hommes aiment Dieu.",
            "score": 0.65,
        },
    ]


def _mock_context(result: dict[str, Any], *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
    """Return a single-verse context for mock tests."""
    return [
        {
            "chapter": result["chapter"],
            "verse": result["verse"],
            "text": result["text"],
            "is_match": True,
        }
    ]


@pytest.fixture
def mock_pipeline() -> Generator[None, None, None]:
    """Patch app pipeline so no models are loaded."""
    with (
        patch("app.pipeline", {"loaded": True, "mapping": [], "verse_index": {}}),
        patch("app._run_search", side_effect=lambda q: _mock_search_results(relevant=True)),
        patch("app.get_verse_context", side_effect=_mock_context),
    ):
        yield


@pytest.fixture
def mock_pipeline_low_scores() -> Generator[None, None, None]:
    """Patch app pipeline with only low-score results."""
    with (
        patch("app.pipeline", {"loaded": True, "mapping": [], "verse_index": {}}),
        patch("app._run_search", side_effect=lambda q: _mock_search_results(relevant=False)),
        patch("app.get_verse_context", side_effect=_mock_context),
    ):
        yield


@pytest.fixture
def client(mock_pipeline: None) -> TestClient:
    """FastAPI test client with mocked pipeline."""
    from app import app as fastapi_app

    return TestClient(fastapi_app)


@pytest.fixture(scope="session")
def pipeline() -> tuple:
    """Load retrieval pipeline once for all integration tests."""
    from rag.retrieve import load_pipeline

    return load_pipeline()
