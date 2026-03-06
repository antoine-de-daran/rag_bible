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

The frontend is at `http://localhost:8000/` (root URL serves `static/index.html`).

## Architecture

French Bible RAG with two-stage retrieval:

1. **`rag/embeddings.py`** -- model abstraction: loads SentenceTransformer (embedding) and CrossEncoder (reranking) models
2. **`rag/ingest.py`** -- ingestion pipeline: reads `bible.db` SQLite, filters short/non-content verses, encodes with SentenceTransformer, builds FAISS IndexFlatIP, writes `data/index.faiss` + `data/mapping.json`
3. **`rag/retrieve.py`** -- two-stage search: FAISS top-K (cosine via inner product on L2-normalized vectors), then cross-encoder reranking with sigmoid score normalization
4. **`config.py`** -- all tunable parameters (paths, model names, thresholds, retrieval K values, `SEARCH_CACHE_SIZE`, `ONNX_FILE_NAME` auto-detected per CPU architecture, `FEEDBACK_ENV` auto-detected from `SPACE_ID`)
5. **`app.py`** -- FastAPI server: loads pipeline in a background thread at startup (UI available immediately, `/search` returns a loading fragment with HTMX auto-retry until ready, `/health` returns 503 while loading). Query sanitization, input validation, contextual verse display with surrounding verses bounded by book_id. LRU cache on `_run_search_cached` (128 entries) makes repeated queries near-instant; `_run_search` returns shallow-copied dicts to prevent cache mutation. Root URL serves SPA, SEO routes (`/robots.txt`, `/sitemap.xml`), static asset cache middleware (24h), HF-to-custom-domain redirect middleware
6. **`rag/feedback.py`** -- per-verse feedback: thread-safe JSONL buffer with periodic flush to HuggingFace Dataset repo via `HfApi.upload_file()`. Config-driven thresholds and intervals. Lazy-imports `huggingface_hub` to avoid startup cost

Data flow: `bible.db` -> ingest -> `data/{index.faiss, mapping.json}` -> app startup spawns background thread to load into memory -> HTMX POST `/search` -> HTML fragment response (or loading fragment if pipeline not yet ready). Root `/` serves the SPA entry point. Feedback: `POST /feedback` -> append to JSONL buffer -> periodic flush to HF Dataset repo (production only).

## Frontend

Custom design system with warm parchment aesthetic (`#f5f0e8` background, `#2a2a2e` dark cards). No build step -- all vanilla HTML/CSS/JS.

- **`static/index.html`** -- single-page HTMX app with semantic HTML, Crimson Text font, offline banner, sidebar toggle, search form, JSON-LD structured data, OG/Twitter meta tags, inline SVG favicon, example queries section
- **`static/styles.css`** -- CSS custom properties (design tokens) in `:root`, mobile-first responsive, `prefers-reduced-motion` support
- **`static/app.js`** -- component initializers inside `DOMContentLoaded`: `initPageHeader`, `initSearchBar`, `initStatusMessages`, `initCarousel`, `initCarouselNavigation`, `initFeedback`, `initHistorySidebar`, `initExampleQueries`, `initScrollHint`, `initOfflineDetection`. Shared state via `window.appState`
- **`static/service-worker.js`** -- cache-first for static assets, network-only for `/search` API
- **`templates/results.html`** -- Embla Carousel structure (viewport > track > slides) with score badges and context verses
- **`templates/loading.html`** -- loading state with HTMX `hx-trigger="load delay:2s"` auto-retry
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
- App tests use `mock_pipeline` fixture from `conftest.py` to avoid loading models; `mock_pipeline_loading` simulates the not-yet-ready state
- `pipeline_ready` is a `threading.Event` in `app.py`; tests patch it with set/unset events
- Docstrings follow numpy convention
- Line length: 100 chars
- Python 3.12+ (uses `X | Y` union syntax)
- Custom domain: `recherche-biblique.com` via Cloudflare Worker reverse proxy to HF Spaces
- HFRedirectMiddleware in `app.py` redirects direct `hf.space` visits to custom domain (uses `X-Original-Host` header to distinguish proxy vs direct traffic)
- Docker exposes port 7860 (HuggingFace Spaces default)
- Version is defined in `pyproject.toml`; also displayed in sidebar (`static/index.html` `.sidebar-version`) -- keep both in sync when bumping
- Per-verse feedback: thumbs up/down on result cards, buffered to JSONL, flushed to HF Dataset repo `adedaran/rag-bible-feedback` every 5 min or 50 records. `POST /feedback` endpoint returns 204 (fire-and-forget). Config in `config.py` (`FEEDBACK_*` constants). `HF_TOKEN` env var required for flush to work. Each record includes a `session_id` (UUID generated client-side via `crypto.randomUUID()` with `Math.random` fallback for older browsers, stored in `sessionStorage` with try/catch for Safari ITP restrictions)
- `FEEDBACK_ENV` auto-detected: `"production"` on HF Spaces (`SPACE_ID` set), `"local"` otherwise. Override with `FEEDBACK_ENV=production`. Local mode writes to `data/feedback_buffer_local.jsonl` and never flushes to HF. Production mode uses `data/feedback_buffer.jsonl` with HF flush. Each record includes a `source` field
