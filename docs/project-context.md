---
project_name: 'rag_bible'
user_name: 'Antoine'
date: '2026-02-22'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality', 'workflow_rules', 'critical_rules']
status: 'complete'
rule_count: 65
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- **Python 3.12+** -- uses `X | Y` union syntax, `uv` package manager (never pip)
- **FastAPI >= 0.115.0** -- async lifespan pattern, Jinja2 HTML fragment responses
- **sentence-transformers >= 3.0.0** -- embedding model: `paraphrase-multilingual-MiniLM-L12-v2` (384d, L2-normalized)
- **cross-encoder** -- `mmarco-mMiniLMv2-L12-H384-v1`, sigmoid score normalization
- **faiss-cpu >= 1.8.0** -- IndexFlatIP (inner product = cosine for normalized vectors)
- **torch >= 2.0.0**, **numpy >= 1.24.0**
- **Jinja2 >= 3.1.0** -- HTML fragment templates for HTMX
- **HTMX + Pico CSS** -- no build step, no SPA, HTML-first frontend
- **ruff >= 0.9.0** (lint + format), **mypy >= 1.13.0** (strict), **pytest >= 8.0.0**
- **Docker** -- Python 3.12-slim, port 7860 (HuggingFace Spaces)

## Critical Implementation Rules

### Language-Specific Rules (Python 3.12+)

- **Type hints mandatory** -- strict mypy; annotate all params, returns, and module constants
- **Union syntax** -- use `X | Y`, never `Optional[X]` or `Union[X, Y]`
- **Import order** -- stdlib > third-party > local, blank line between groups
- **Path handling** -- always `pathlib.Path`, never `os.path`
- **Private imports** -- rename with underscore: `from mod import func as _func`
- **Error handling** -- `try/except Exception` + `logger.exception()`; never expose tracebacks
- **Input validation chain** -- sanitize (strip HTML/null bytes) -> truncate -> validate (min words) -> error response
- **Docstrings** -- NumPy convention (`Parameters`, `Returns` sections) on all public functions; skip in tests
- **Constants** -- ALL_CAPS with type annotations: `FAISS_TOP_K: int = 20`
- **Private module state** -- prefix with underscore: `_DEFAULT_CORS`

### Framework-Specific Rules (FastAPI + HTMX)

- **Lifespan pattern** -- use `@asynccontextmanager` lifespan, not `@app.on_event`; load models once into module-level `pipeline` dict
- **HTML fragment responses** -- endpoints return `templates.TemplateResponse()`, never JSON
- **Form input** -- use `Form(...)` for HTMX POST bodies, not Pydantic models
- **Three response templates** -- `results.html`, `no_results.html`, `error.html` in `templates/`
- **Template context** -- always include `request` object (Starlette requirement)
- **Custom Jinja2 filter** -- `nl2br`: html-escape first via `markupsafe`, then `\n` -> `<br>`
- **CORS** -- configured via `CORS_ORIGINS` env var, parsed in `config.py`
- **Frontend path** -- served at `/static/index.html`, not root `/`
- **No router splitting** -- single `app.py` file; endpoints: `/health` (GET), `/search` (POST)

### Testing Rules

- **File per module** -- `test_<module>.py`; integration tests in `test_integration.py`
- **Two markers** -- `unit` (default, no models) and `integration` (requires models + `data/`); never run integration by accident
- **Class-grouped tests** -- group by feature: `TestSanitizeQuery`, `TestHealthEndpoint`
- **Mock pipeline** -- always patch `app.pipeline` + `app._run_search` in app tests; never load real models in unit tests
- **Fixture pattern** -- yield inside `with patch(...)` context manager; use `side_effect` for dynamic mocks
- **Shared fixtures** -- in `conftest.py`: `sample_verses`, `sample_texts`, `tmp_data_dir`, `mock_pipeline`, `client`
- **No docstrings in tests** -- configured via ruff `per-file-ignores` on `tests/*`
- **Run before commit** -- `make test-unit` (fast) or `make test-all` (full); pre-commit hooks run ruff + mypy

### Code Quality & Style Rules

- **Line length** -- 100 characters (ruff enforced)
- **Ruff rules** -- `E`, `F`, `W`, `I`, `UP`, `D`; auto-fix with `make format`
- **Naming** -- snake_case everywhere; ALL_CAPS for constants; no classes (functional architecture)
- **File naming** -- lowercase with underscores: `embeddings.py`, `test_retrieve.py`
- **Single config source** -- all tunable parameters in `config.py`; never hardcode paths or thresholds
- **Module organization** -- `rag/` package: one file per concern; `app.py` flat (no routers)
- **Pre-commit** -- ruff check + format + mypy run automatically; fix issues before committing
- **Check command** -- `make check` runs lint + typecheck in one shot

### Development Workflow Rules

- **Package manager** -- `uv` only; all Python commands via `uv run`, never `pip` or bare `python`
- **Branch naming** -- `feature/<desc>`, `fix/<desc>`, `chore/<desc>`
- **Commits** -- Conventional Commits format; under 69 chars; no emojis or AI references
- **Pre-commit hooks** -- ruff check + format + mypy; runs automatically on commit
- **Data artifacts gitignored** -- `data/` not in repo; regenerate with `make ingest` (needs `bible.db`)
- **Dev server** -- `make serve` at `localhost:8000`; frontend at `/static/index.html`
- **Docker** -- port 7860 (HF Spaces default); `make docker-build` + `make docker-serve`
- **CORS** -- set `CORS_ORIGINS` env var for deployment; defaults cover localhost

### Critical Don't-Miss Rules

- **Verse context boundary** -- `get_verse_context()` must NEVER cross `book_id` boundaries; always bounds-check
- **Sigmoid normalization** -- cross-encoder outputs raw logits; apply sigmoid to get [0, 1] scores (0.5 = decision boundary)
- **FAISS = cosine only if normalized** -- IndexFlatIP assumes L2-normalized vectors; always normalize before indexing
- **Ingestion dual filter** -- verses must pass BOTH min 10 chars AND min 3 words
- **Query min 5 words** -- enforced after sanitization, with client-side hint + backend validation
- **nl2br XSS prevention** -- html-escape FIRST (`markupsafe.escape`), THEN convert `\n` to `<br>`; order is critical
- **Never expose tracebacks** -- catch all exceptions in endpoints, log with `logger.exception()`, return generic error template
- **No JSON endpoints** -- all responses are Jinja2 HTML fragments; HTMX expects HTML, not JSON
- **Models loaded once** -- via lifespan into `pipeline` dict; never reload per-request
- **Data flow** -- `bible.db` -> `make ingest` -> `data/{index.faiss, mapping.json}` -> app startup loads into memory

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Update this file if new patterns emerge

**For Humans:**

- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review periodically for outdated rules
- Remove rules that become obvious over time

Last Updated: 2026-02-22
