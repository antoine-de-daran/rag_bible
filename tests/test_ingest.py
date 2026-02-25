from pathlib import Path
from typing import Any

import pytest

import config


@pytest.mark.unit
def test_fetch_verses_returns_all_rows() -> None:
    """fetch_verses reads all rows from bible.db."""
    from rag.ingest import fetch_verses

    verses = fetch_verses(config.DB_PATH)
    assert len(verses) == 35480


@pytest.mark.unit
def test_fetch_verses_has_rowid() -> None:
    """Each verse dict includes a rowid key."""
    from rag.ingest import fetch_verses

    verses = fetch_verses(config.DB_PATH)
    assert "rowid" in verses[0]


@pytest.mark.unit
def test_filter_verses_removes_short_text(
    sample_verses: list[dict[str, Any]],
) -> None:
    """Verses with text shorter than MIN_TEXT_LENGTH are filtered out."""
    from rag.ingest import filter_verses

    result = filter_verses(sample_verses, min_length=10, min_words=3)
    texts = [v["text"] for v in result]
    assert "LUI" not in texts
    assert "ELLE" not in texts
    assert "[" not in texts


@pytest.mark.unit
def test_filter_verses_removes_few_words(
    sample_verses: list[dict[str, Any]],
) -> None:
    """Verses with fewer than MIN_WORD_COUNT words are filtered out."""
    from rag.ingest import filter_verses

    result = filter_verses(sample_verses, min_length=10, min_words=3)
    texts = [v["text"] for v in result]
    # "Alléluia" is only 1 word (8 chars < 10), filtered by length
    assert "Alléluia" not in texts
    # "30 500 ânes," is 3 words and 12 chars -- should pass
    assert any("30 500" in t for t in texts)


@pytest.mark.unit
def test_filter_verses_keeps_valid(
    sample_verses: list[dict[str, Any]],
) -> None:
    """Normal verses pass both filters."""
    from rag.ingest import filter_verses

    result = filter_verses(sample_verses, min_length=10, min_words=3)
    texts = [v["text"] for v in result]
    assert any("COMMENCEMENT" in t for t in texts)
    assert any("lumière" in t for t in texts)


@pytest.mark.integration
def test_ingest_creates_artifacts(tmp_data_dir: Path) -> None:
    """Full ingestion creates index.faiss and mapping.json with matching sizes."""
    import json

    import faiss

    from rag.ingest import main

    index_path = tmp_data_dir / "index.faiss"
    mapping_path = tmp_data_dir / "mapping.json"

    main(
        db_path=config.DB_PATH,
        index_path=index_path,
        mapping_path=mapping_path,
    )

    assert index_path.exists()
    assert mapping_path.exists()

    index = faiss.read_index(str(index_path))
    with open(mapping_path) as f:
        mapping = json.load(f)

    assert index.ntotal == len(mapping)
    assert index.ntotal > 30000  # most verses should survive filtering
