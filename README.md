---
title: RAG Bible
emoji: "\U0001F4D6"
colorFrom: yellow
colorTo: brown
sdk: docker
app_port: 7860
pinned: false
---

# RAG Bible

Retrieval-Augmented Generation system for the French Bible (AELF translation). Uses FAISS for vector search and a cross-encoder for reranking, served via FastAPI with an HTMX frontend.

## Architecture

1. **Ingestion** (`ingest.py`): reads `bible.db`, filters non-content verses, embeds text with a multilingual sentence transformer, builds a FAISS index + JSON mapping.
2. **Retrieval** (`retrieve.py`): two-stage search -- FAISS top-K candidates, then cross-encoder reranking for precision.
3. **Web** (`app.py`): FastAPI backend serving Jinja2 HTML fragments. Static HTMX + Pico CSS frontend.

## Project Structure

```
bible.db          # SQLite database with 35,480 French Bible verses
config.py         # Central configuration (paths, model names, parameters)
embeddings.py     # Model loading and text encoding
ingest.py         # Ingestion pipeline: filter, embed, index
retrieve.py       # Two-stage retrieval: FAISS + cross-encoder rerank
app.py            # FastAPI application
templates/        # Jinja2 HTML fragments (results, errors)
static/           # Frontend (index.html with HTMX + Pico CSS)
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
make ingest       # build FAISS index from bible.db (~1 min)
make serve        # start dev server at http://localhost:8000
```

Open `http://localhost:8000/static/index.html` in your browser.

## API Endpoints

- `GET /health` -- health check, returns `{"status": "ok"}`
- `POST /search` -- accepts `query` form field, returns HTML fragment

## Testing

```bash
make test-unit    # run unit tests (fast, no models needed)
make test-all     # run all tests including integration
make check        # lint + type check
```

## Docker

```bash
make docker-build   # build image
make docker-serve   # run on port 7860 (HuggingFace Spaces default)
```

## Models

- **Embedding**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384d)
- **Cross-encoder**: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (multilingual, mMARCO-trained)
