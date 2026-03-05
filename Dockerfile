FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY config.py ./
COPY rag/ rag/

# Pre-download and load quantized ONNX models at build time (cached in layer)
RUN uv run python -c "\
from rag.embeddings import load_embedding_model, load_cross_encoder; \
print('Loading embedding model...'); load_embedding_model(); \
print('Loading cross-encoder...'); load_cross_encoder(); \
print('Models cached.')"

COPY app.py ./
COPY templates/ templates/
COPY static/ static/
COPY data/ data/

EXPOSE 7860

CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
