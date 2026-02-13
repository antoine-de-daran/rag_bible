"""Atomic ingestion script: filter, embed, and index Bible verses."""

import json
import sqlite3
from pathlib import Path
from typing import Any

import faiss
from sentence_transformers import SentenceTransformer

import config
from embeddings import encode_texts, load_embedding_model


def fetch_verses(db_path: Path) -> list[dict[str, Any]]:
    """Fetch all verses from the SQLite database.

    Parameters
    ----------
    db_path : Path
        Path to the SQLite database file.

    Returns
    -------
    list[dict[str, Any]]
        List of verse dicts with rowid and all column values.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT rowid, book, book_id, book_title, chapter, chapter_id, "
        "chapter_title, verse, text FROM verses"
    )
    verses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return verses


def filter_verses(
    verses: list[dict[str, Any]],
    min_length: int = config.MIN_TEXT_LENGTH,
    min_words: int = config.MIN_WORD_COUNT,
) -> list[dict[str, Any]]:
    """Filter out non-content verses based on text length and word count.

    Parameters
    ----------
    verses : list[dict[str, Any]]
        Raw verse dicts from the database.
    min_length : int
        Minimum character length for verse text.
    min_words : int
        Minimum word count for verse text.

    Returns
    -------
    list[dict[str, Any]]
        Filtered verse dicts.
    """
    return [
        v for v in verses if len(v["text"]) >= min_length and len(v["text"].split()) >= min_words
    ]


def build_mapping(verses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the verse metadata mapping from filtered verses.

    Parameters
    ----------
    verses : list[dict[str, Any]]
        Filtered verse dicts.

    Returns
    -------
    list[dict[str, Any]]
        Mapping entries preserving all metadata and original text.
    """
    return [
        {
            "rowid": v["rowid"],
            "book": v["book"],
            "book_id": v["book_id"],
            "book_title": v["book_title"],
            "chapter": v["chapter"],
            "chapter_id": v["chapter_id"],
            "chapter_title": v["chapter_title"],
            "verse": v["verse"],
            "text": v["text"],
        }
        for v in verses
    ]


def build_index(
    texts: list[str],
    model: SentenceTransformer,
    dimension: int = config.EMBEDDING_DIMENSION,
) -> faiss.Index:
    """Embed texts and build a FAISS inner-product index.

    Parameters
    ----------
    texts : list[str]
        Texts to embed.
    model : SentenceTransformer
        Loaded embedding model.
    dimension : int
        Embedding dimension.

    Returns
    -------
    faiss.Index
        FAISS IndexFlatIP with all embeddings added.
    """
    embeddings = encode_texts(model, texts)
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    return index


def save_artifacts(
    index: faiss.Index,
    mapping: list[dict[str, Any]],
    index_path: Path,
    mapping_path: Path,
) -> None:
    """Save FAISS index and JSON mapping to disk.

    Parameters
    ----------
    index : faiss.Index
        FAISS index to save.
    mapping : list[dict[str, Any]]
        Verse metadata mapping.
    index_path : Path
        Output path for the FAISS index file.
    mapping_path : Path
        Output path for the JSON mapping file.
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def main(
    db_path: Path = config.DB_PATH,
    index_path: Path = config.INDEX_PATH,
    mapping_path: Path = config.MAPPING_PATH,
) -> None:
    """Run the full ingestion pipeline.

    Parameters
    ----------
    db_path : Path
        Path to the SQLite database.
    index_path : Path
        Output path for the FAISS index.
    mapping_path : Path
        Output path for the JSON mapping.
    """
    print(f"Fetching verses from {db_path}")
    verses = fetch_verses(db_path)
    print(f"  Total verses: {len(verses)}")

    filtered = filter_verses(verses)
    print(f"  After filtering: {len(filtered)}")

    mapping = build_mapping(filtered)
    texts = [v["text"] for v in filtered]

    print("Loading embedding model...")
    model = load_embedding_model()

    print("Building FAISS index...")
    index = build_index(texts, model)
    print(f"  Index size: {index.ntotal}")

    print(f"Saving artifacts to {index_path.parent}")
    save_artifacts(index, mapping, index_path, mapping_path)
    print("Done.")


if __name__ == "__main__":
    main()
