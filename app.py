"""FastAPI application serving the RAG Bible search interface."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
from rag.retrieve import load_pipeline as _load_pipeline
from rag.retrieve import search as _search

# Module-level state set during lifespan
pipeline: dict[str, Any] = {}

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def get_score_label(score: float) -> str:
    """Return a French relevance label for the given score.

    Parameters
    ----------
    score : float
        Normalized score in [0, 1].

    Returns
    -------
    str
        Human-readable relevance label.
    """
    for threshold, label in config.SCORE_LABELS:
        if score >= threshold:
            return label
    return config.SCORE_LABELS[-1][1]


def _run_search(query: str) -> list[dict[str, Any]]:
    """Run the retrieval pipeline on a query."""
    return _search(
        query,
        pipeline["index"],
        pipeline["mapping"],
        pipeline["embed_model"],
        pipeline["cross_encoder"],
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Load models once at startup."""
    index, mapping, embed_model, cross_encoder = _load_pipeline()
    pipeline["index"] = index
    pipeline["mapping"] = mapping
    pipeline["embed_model"] = embed_model
    pipeline["cross_encoder"] = cross_encoder
    pipeline["loaded"] = True
    yield
    pipeline.clear()


app = FastAPI(title="RAG Bible", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/health")  # type: ignore[misc]
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/search", response_class=HTMLResponse)  # type: ignore[misc]
def search_endpoint(request: Request, query: str = Form("")) -> HTMLResponse:
    """Search the Bible and return an HTML fragment."""
    trimmed = query.strip()[: config.MAX_QUERY_LENGTH]

    if not trimmed:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"message": "Veuillez saisir une question ou un mot-cle."},
        )

    results = _run_search(trimmed)

    relevant = [r for r in results if r["score"] >= config.RELEVANCE_THRESHOLD]

    if not relevant:
        return templates.TemplateResponse(
            request=request,
            name="no_results.html",
            context={"query": trimmed},
        )

    for r in relevant:
        r["label"] = get_score_label(r["score"])
        r["pct"] = int(r["score"] * 100)

    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={"results": relevant, "query": trimmed},
    )
