# RAG Bible

Retrieval-Augmented Generation system for the French Bible (AELF translation). Uses FAISS for vector search and a cross-encoder for reranking.

## Architecture

1. **Ingestion** (`ingest.py`): reads `bible.db`, filters non-content verses, embeds text with a multilingual sentence transformer, builds a FAISS index + JSON mapping.
2. **Retrieval** (`retrieve.py`): two-stage search -- FAISS top-K candidates, then cross-encoder reranking for precision.

## Project Structure

```
bible.db          # SQLite database with 35,480 French Bible verses
config.py         # Central configuration (paths, model names, parameters)
embeddings.py     # Model loading and text encoding
ingest.py         # Ingestion pipeline: filter, embed, index
retrieve.py       # Two-stage retrieval: FAISS + cross-encoder rerank
tests/            # Test suite (unit + integration)
data/             # Generated artifacts (gitignored)
  index.faiss     # FAISS vector index
  mapping.json    # Verse metadata mapping
```

## Setup

```bash
make install      # install dependencies + pre-commit hooks
```

## Usage

```bash
make ingest       # build FAISS index from bible.db (~2-4 min)
make test-unit    # run unit tests (fast, no models needed)
make test-all     # run all tests including integration
make check        # lint + type check
```

## Models

- **Embedding**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384d)
- **Cross-encoder**: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (multilingual, mMARCO-trained)
