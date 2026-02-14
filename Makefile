.PHONY: install test-unit test-integration test-all ingest lint typecheck check format serve docker-build docker-serve docker-run-ingest docker-run-test clean

install:
	uv sync
	uv run pre-commit install

test-unit:
	uv run pytest -m "not integration"

test-integration:
	uv run pytest -m integration

test-all:
	uv run pytest

ingest:
	uv run python -m rag.ingest

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy config.py rag/ app.py

check: lint typecheck

format:
	uv run ruff format .
	uv run ruff check --fix .

serve:
	uv run uvicorn app:app --reload --port 8000

docker-build:
	docker build -t rag-bible .

docker-serve:
	docker run --rm -p 7860:7860 rag-bible

docker-run-ingest:
	docker run --rm -v $(PWD)/data:/app/data rag-bible python ingest.py

docker-run-test:
	docker run --rm rag-bible pytest

clean:
	rm -rf data/
