FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY bible.db config.py embeddings.py ingest.py retrieve.py ./
COPY tests/ tests/

CMD ["uv", "run", "pytest"]
