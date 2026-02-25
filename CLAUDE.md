# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands use `uv` (not pip). Prefix Python invocations with `uv run`.

```bash
make install          # install deps + pre-commit hooks
make ingest           # build FAISS index from bible.db (~1 min)
make serve            # dev server at http://localhost:8000 (reload enabled)
make test-unit        # unit tests only (default, no models needed)
make test-integration # integration tests (requires models + data/)
make test-all         # all tests
make lint             # ruff check + format check
make typecheck        # mypy strict on config.py rag/ app.py
make check            # lint + typecheck
make format           # auto-fix ruff format + lint
```

Run a single test: `uv run pytest tests/test_app.py::test_name -v`

The frontend is at `http://localhost:8000/static/index.html` (not the root `/`).

## Architecture

French Bible RAG with two-stage retrieval:

1. **`rag/embeddings.py`** -- model abstraction: loads SentenceTransformer (embedding) and CrossEncoder (reranking) models
2. **`rag/ingest.py`** -- ingestion pipeline: reads `bible.db` SQLite, filters short/non-content verses, encodes with SentenceTransformer, builds FAISS IndexFlatIP, writes `data/index.faiss` + `data/mapping.json`
3. **`rag/retrieve.py`** -- two-stage search: FAISS top-K (cosine via inner product on L2-normalized vectors), then cross-encoder reranking with sigmoid score normalization
4. **`config.py`** -- all tunable parameters (paths, model names, thresholds, retrieval K values)
5. **`app.py`** -- FastAPI server: loads pipeline once at startup via lifespan, serves Jinja2 HTML fragments to HTMX frontend. Query sanitization, input validation, contextual verse display with surrounding verses bounded by book_id

Data flow: `bible.db` -> ingest -> `data/{index.faiss, mapping.json}` -> app startup loads into memory -> HTMX POST `/search` -> HTML fragment response.

## Frontend

Custom design system with warm parchment aesthetic (`#f5f0e8` background, `#2a2a2e` dark cards). No build step -- all vanilla HTML/CSS/JS.

- **`static/index.html`** -- single-page HTMX app with semantic HTML, Crimson Text font, offline banner, sidebar toggle, search form
- **`static/styles.css`** -- CSS custom properties (design tokens) in `:root`, mobile-first responsive, `prefers-reduced-motion` support
- **`static/app.js`** -- component initializers inside `DOMContentLoaded`: `initPageHeader`, `initSearchBar`, `initStatusMessages`, `initCarousel`, `initCarouselNavigation`, `initHistorySidebar`, `initOfflineDetection`. Shared state via `window.appState`
- **`static/service-worker.js`** -- cache-first for static assets, network-only for `/search` API
- **`templates/results.html`** -- Embla Carousel structure (viewport > track > slides) with score badges and context verses
- **`templates/error.html`** -- error message with "Reessayer" retry button
- **`templates/no_results.html`** -- simple no-results feedback

### Frontend Conventions

- JS naming: `camelCase` variables/functions, `initPascalCase` for component initializers, `SCREAMING_SNAKE_CASE` for constants
- CSS naming: `kebab-case` for component classes (`.search-bar`, `.result-card`), single-word for states (`.active`, `.hidden`)
- Component pattern: each `initX(appState)` caches DOM refs, attaches listeners, returns public API stored on `appState`
- Use `const` (never `var`), `aria-disabled` (not `disabled` attribute) for buttons that must allow Enter key submission
- CDN dependencies: HTMX 2.0.4, Embla Carousel 8.0.0, Google Fonts Crimson Text
- localStorage key `"bible_search_history"` for search history (max 20 entries)
- Touch targets: 44px mobile, 40px desktop. All transitions 350ms ease-out

## Key Conventions

- Embeddings are always L2-normalized; FAISS uses IndexFlatIP (inner product = cosine for normalized vectors)
- Cross-encoder raw scores are sigmoid-normalized to [0, 1] (0.5 = decision boundary)
- `data/` is gitignored -- regenerate with `make ingest` (requires `bible.db` in `data/`)
- Tests use two markers: `unit` (fast, mocked, default) and `integration` (loads real models + data)
- App tests use `mock_pipeline` fixture from `conftest.py` to avoid loading models
- Docstrings follow numpy convention
- Line length: 100 chars
- Python 3.12+ (uses `X | Y` union syntax)
- Docker exposes port 7860 (HuggingFace Spaces default)
