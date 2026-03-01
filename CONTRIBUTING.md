# Contributing

Thanks for your interest in contributing to RAG Bible. This guide covers
how to set up the project, submit changes, and follow the conventions
used in this codebase.

## Getting started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (not pip)
- Git

### Setup

```bash
git clone https://github.com/<your-fork>/rag_bible.git
cd rag_bible
make install   # installs deps + pre-commit hooks
```

To build the FAISS index (requires `bible.db` in `data/`):

```bash
make ingest
```

To start the dev server:

```bash
make serve     # http://localhost:8000
```

## How to contribute

### 1. Open an issue first

Before writing code, open an issue to discuss your idea. This avoids
duplicate work and lets us align on the approach early. Describe:

- **Bug reports**: steps to reproduce, expected vs. actual behavior
- **Feature requests**: use case, proposed behavior, any alternatives
  you considered
- **Documentation**: what's missing or unclear

Small typo fixes can skip this step and go straight to a PR.

### 2. Fork and branch

Fork the repository and create a branch from `master`:

```bash
git checkout -b feature/your-description   # new feature
git checkout -b fix/your-description       # bug fix
git checkout -b docs/your-description      # documentation
git checkout -b chore/your-description     # maintenance
```

### 3. Make your changes

Write your code following the conventions below, then verify everything
passes:

```bash
make check       # ruff lint + mypy typecheck
make test-unit   # fast unit tests (no models needed)
```

If your change touches retrieval logic or the ingestion pipeline, also
run integration tests (requires models and `data/`):

```bash
make test-integration
```

### 4. Commit

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(rag): add book-level filtering to retrieval
fix(ui): correct carousel swipe on mobile
docs: update setup instructions in README
refactor: extract query sanitization into helper
test: add unit tests for context verse boundaries
chore: update ruff to 0.10
```

Rules:
- Keep the subject line under 69 characters
- Use the imperative mood ("add", not "added")
- No emojis

Pre-commit hooks will run `ruff` and `mypy` automatically. If a hook
fails, fix the issue and commit again.

### 5. Open a pull request

Push your branch and open a PR against `master`. In the PR description,
reference the issue it addresses (e.g., "Closes #12") and include:

- A short summary of what changed and why
- How to test the change
- Screenshots if the change is visual

## Code conventions

### Python

- Line length: 100 characters
- Docstrings: numpy convention
- Type hints everywhere (mypy strict mode)
- Linter: ruff (`E`, `F`, `W`, `I`, `UP`, `D` rules)
- `X | Y` union syntax (Python 3.12+)
- Config values in `config.py`, passed as arguments (no global mutable
  state)

### Frontend

- No build step -- vanilla HTML, CSS, JS
- JS: `camelCase` functions/variables, `initPascalCase` for component
  initializers, `SCREAMING_SNAKE_CASE` for constants
- CSS: `kebab-case` class names, custom properties for design tokens
- `const` only (never `var`)
- Touch targets: 44px mobile, 40px desktop

### Tests

- Mark fast tests with `@pytest.mark.unit`
- Mark tests needing models/data with `@pytest.mark.integration`
- Use the `mock_pipeline` fixture from `conftest.py` for app tests
- `make test-unit` runs by default (no models required)

### Git

- Branch from `master`
- One logical change per commit
- Rebase on `master` before opening a PR to keep history linear

## What can I work on?

Look at open issues, especially those labeled `good first issue` or
`help wanted`. If nothing matches your interest, open a new issue to
propose your idea.

Areas where contributions are welcome:

- Bug fixes and test coverage improvements
- Documentation and examples
- Performance optimizations (retrieval, indexing)
- Frontend accessibility and UX improvements
- New features (discussed via issue first)
- Translations and i18n support

## Questions?

Open an issue. We're happy to help.
