"""Benchmark comparing MiniLM vs bge-m3 embedding models for Bible search."""

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

import faiss as faiss_lib

import config
from rag.embeddings import load_cross_encoder, load_embedding_model
from rag.ingest import build_index, build_mapping, fetch_verses, filter_verses, save_artifacts
from rag.retrieve import search

logger = logging.getLogger(__name__)

MODELS: dict[str, dict[str, Any]] = {
    "MiniLM": {
        "name": config.EMBEDDING_MODEL,
        "dimension": 384,
        "index_path": config.INDEX_PATH,
        "mapping_path": config.MAPPING_PATH,
    },
    "bge-m3": {
        "name": "BAAI/bge-m3",
        "dimension": 1024,
        "index_path": config.DATA_DIR / "index_bge_m3.faiss",
        "mapping_path": config.DATA_DIR / "mapping_bge_m3.json",
    },
}

QUERIES: list[dict[str, str]] = [
    {"category": "basic_topic", "text": "Que dit la Bible sur l'amour de Dieu"},
    {
        "category": "complex_theology",
        "text": "Comment la grace divine opere-t-elle dans la redemption des pecheurs",
    },
    {
        "category": "proper_noun",
        "text": "Quelles sont les paroles de Moise devant le buisson ardent",
    },
    {
        "category": "poetic_language",
        "text": "Les images poetiques de la nature dans les Psaumes de louange",
    },
    {
        "category": "cross_testament",
        "text": "La promesse d'un messie dans les propheties et son accomplissement",
    },
    {
        "category": "moral_teaching",
        "text": "Comment la Bible enseigne-t-elle le pardon envers ses ennemis",
    },
    {"category": "narrative_event", "text": "Le recit de la multiplication des pains par Jesus"},
    {
        "category": "wisdom_literature",
        "text": "La sagesse et la crainte de Dieu dans les Proverbes de Salomon",
    },
    {
        "category": "eschatology",
        "text": "Les signes de la fin des temps dans l'Apocalypse de Jean",
    },
    {
        "category": "daily_life",
        "text": "Que dit la Bible sur le travail et la perseverance quotidienne",
    },
]


def ingest_model(
    model_key: str,
    verses: list[dict[str, Any]],
    mapping: list[dict[str, Any]],
    texts: list[str],
    force: bool = False,
) -> dict[str, Any]:
    """Build FAISS index for a model, skipping if artifacts exist on disk.

    Returns
    -------
    dict[str, Any]
        Stats: model_load_time, ingest_time, index_size_mb, vector_count.
    """
    info = MODELS[model_key]
    index_path: Path = info["index_path"]
    mapping_path: Path = info["mapping_path"]

    if index_path.exists() and mapping_path.exists() and not force:
        size_mb = index_path.stat().st_size / (1024 * 1024)
        logger.info("[%s] Artifacts exist, skipping ingest (%.1f MB)", model_key, size_mb)
        return {
            "model_load_time": 0.0,
            "ingest_time": 0.0,
            "index_size_mb": size_mb,
            "vector_count": len(mapping),
            "skipped": True,
        }

    t0 = time.perf_counter()
    model = load_embedding_model(info["name"])
    model_load_time = time.perf_counter() - t0
    logger.info("[%s] Model loaded in %.1fs", model_key, model_load_time)

    t0 = time.perf_counter()
    index = build_index(texts, model, dimension=info["dimension"])
    ingest_time = time.perf_counter() - t0
    logger.info("[%s] Index built in %.1fs (%d vectors)", model_key, ingest_time, index.ntotal)

    save_artifacts(index, mapping, index_path, mapping_path)
    size_mb = index_path.stat().st_size / (1024 * 1024)
    logger.info("[%s] Saved: %.1f MB", model_key, size_mb)

    return {
        "model_load_time": model_load_time,
        "ingest_time": ingest_time,
        "index_size_mb": size_mb,
        "vector_count": index.ntotal,
        "skipped": False,
    }


def query_model(
    model_key: str,
    cross_encoder: Any,
    queries: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Run all benchmark queries through a model's pipeline.

    Returns
    -------
    list[dict[str, Any]]
        Per-query results: category, text, latency, results.
    """
    info = MODELS[model_key]
    index_path: Path = info["index_path"]
    mapping_path: Path = info["mapping_path"]

    index = faiss_lib.read_index(str(index_path))
    with open(mapping_path, encoding="utf-8") as f:
        mapping: list[dict[str, Any]] = json.load(f)

    embed_model = load_embedding_model(info["name"])

    query_results = []
    for q in queries:
        t0 = time.perf_counter()
        results = search(
            q["text"],
            index,
            mapping,
            embed_model,
            cross_encoder,
        )
        latency = time.perf_counter() - t0
        query_results.append(
            {
                "category": q["category"],
                "text": q["text"],
                "latency": latency,
                "results": results,
            }
        )
        logger.info("[%s] Query '%s' -> %.3fs", model_key, q["category"], latency)

    return query_results


def format_ref(r: dict[str, Any]) -> str:
    """Format a verse reference like 'Jean 3:16'."""
    ref: str = r["book_title"]
    if r["chapter"]:
        ref += f" {r['chapter']}"
    if r["verse"]:
        ref += f":{r['verse']}"
    return ref


def display_results(
    all_results: dict[str, list[dict[str, Any]]],
    ingest_stats: dict[str, dict[str, Any]],
) -> None:
    """Print side-by-side comparison of results."""
    sep = "=" * 100
    model_keys = list(all_results.keys())

    # Ingest summary
    print(f"\n{sep}")
    print("INGEST SUMMARY")
    print(sep)
    for key in model_keys:
        stats = ingest_stats[key]
        status = "skipped" if stats.get("skipped") else "built"
        print(
            f"  {key:>8}: {stats['index_size_mb']:6.1f} MB | "
            f"{stats['vector_count']} vectors | "
            f"model_load={stats['model_load_time']:.1f}s | "
            f"ingest={stats['ingest_time']:.1f}s ({status})"
        )

    # Per-query comparison
    num_queries = len(QUERIES)
    for i in range(num_queries):
        print(f"\n{sep}")
        q = QUERIES[i]
        latencies = " | ".join(f"{k}={all_results[k][i]['latency']:.3f}s" for k in model_keys)
        print(f"Query {i + 1} [{q['category']}]: {q['text']}")
        print(f"Latency: {latencies}")
        print(sep)

        # Column headers
        col_w = 48
        header = " | ".join(f"{k:^{col_w}}" for k in model_keys)
        divider = " | ".join("-" * col_w for _ in model_keys)
        print(f"     {header}")
        print(f"     {divider}")

        max_results = max(len(all_results[k][i]["results"]) for k in model_keys)
        for rank in range(max_results):
            parts = []
            for k in model_keys:
                results = all_results[k][i]["results"]
                if rank < len(results):
                    r = results[rank]
                    ref = format_ref(r)
                    entry = f"[{r['score']:.3f}] {ref}"
                    parts.append(f"{entry:<{col_w}}")
                else:
                    parts.append(" " * col_w)
            print(f"  {rank + 1}. {' | '.join(parts)}")

    # Summary statistics
    print(f"\n{sep}")
    print("SUMMARY")
    print(sep)
    for key in model_keys:
        lats: list[float] = [r["latency"] for r in all_results[key]]
        top1_scores: list[float] = [
            r["results"][0]["score"] if r["results"] else 0.0 for r in all_results[key]
        ]
        avg_latency = sum(lats) / len(lats)
        avg_top1 = sum(top1_scores) / len(top1_scores)
        print(f"  {key:>8}: avg_latency={avg_latency:.3f}s | avg_top1_score={avg_top1:.3f}")
    print()


def main() -> None:
    """Run the full benchmark."""
    parser = argparse.ArgumentParser(description="Benchmark MiniLM vs bge-m3")
    parser.add_argument(
        "--force-ingest", action="store_true", help="Rebuild indexes even if they exist"
    )
    parser.add_argument(
        "--skip-ingest", action="store_true", help="Skip ingest phase (indexes must exist)"
    )
    args = parser.parse_args()

    # Prepare verses (shared across both models)
    logger.info("Fetching and filtering verses...")
    verses = fetch_verses(config.DB_PATH)
    filtered = filter_verses(verses)
    mapping = build_mapping(filtered)
    texts = [v["text"] for v in filtered]
    logger.info("Verses: %d total, %d after filtering", len(verses), len(filtered))

    # Phase 1: Ingest
    ingest_stats: dict[str, dict[str, Any]] = {}
    if not args.skip_ingest:
        for model_key in MODELS:
            ingest_stats[model_key] = ingest_model(
                model_key, verses, mapping, texts, force=args.force_ingest
            )
    else:
        for model_key in MODELS:
            index_path: Path = MODELS[model_key]["index_path"]
            if not index_path.exists():
                logger.error(
                    "[%s] Index not found at %s. Run without --skip-ingest.",
                    model_key,
                    index_path,
                )
                return
            size_mb = index_path.stat().st_size / (1024 * 1024)
            ingest_stats[model_key] = {
                "model_load_time": 0.0,
                "ingest_time": 0.0,
                "index_size_mb": size_mb,
                "vector_count": len(mapping),
                "skipped": True,
            }

    # Phase 2: Query
    logger.info("Loading cross-encoder (shared)...")
    cross_encoder = load_cross_encoder()

    all_results: dict[str, list[dict[str, Any]]] = {}
    for model_key in MODELS:
        logger.info("Running queries with %s...", model_key)
        all_results[model_key] = query_model(model_key, cross_encoder, QUERIES)

    # Phase 3: Display
    display_results(all_results, ingest_stats)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    # Suppress noisy transformer logs
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    main()
