"""FastAPI application serving the RAG Bible search interface."""

import logging
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from html import escape as html_escape
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

import config
from rag.retrieve import load_pipeline as _load_pipeline
from rag.retrieve import search as _search

logger = logging.getLogger(__name__)

# Module-level state set during lifespan
pipeline: dict[str, Any] = {}

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def sanitize_query(raw: str) -> str:
    """Sanitize user query input.

    Parameters
    ----------
    raw : str
        Raw user input.

    Returns
    -------
    str
        Cleaned query string.
    """
    text = raw.strip()
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("\x00", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[: config.MAX_QUERY_LENGTH]


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


def get_verse_context(
    result: dict[str, Any],
    mapping: list[dict[str, Any]],
    verse_index: dict[tuple[str, str, str], int],
    n: int = config.CONTEXT_VERSES,
) -> list[dict[str, Any]]:
    """Return surrounding verses for context display.

    Parameters
    ----------
    result : dict[str, Any]
        A search result with book_title, chapter, verse, text.
    mapping : list[dict[str, Any]]
        Full verse mapping list.
    verse_index : dict[tuple[str, str, str], int]
        Reverse index from (book_title, chapter, verse) to mapping index.
    n : int
        Number of context verses before and after.

    Returns
    -------
    list[dict[str, Any]]
        Context verses, each with chapter, verse, text, is_match.
    """
    key = (result["book_title"], result["chapter"], result["verse"])
    idx = verse_index.get(key)

    if idx is None:
        return [
            {
                "chapter": result["chapter"],
                "verse": result["verse"],
                "text": result["text"],
                "is_match": True,
            }
        ]

    matched_book_id = mapping[idx]["book_id"]
    start = idx
    while start > idx - n and start > 0 and mapping[start - 1]["book_id"] == matched_book_id:
        start -= 1

    end = idx
    while (
        end < idx + n and end < len(mapping) - 1 and mapping[end + 1]["book_id"] == matched_book_id
    ):
        end += 1

    context = []
    for i in range(start, end + 1):
        entry = mapping[i]
        context.append(
            {
                "chapter": entry["chapter"],
                "verse": entry["verse"],
                "text": entry["text"],
                "is_match": i == idx,
            }
        )
    return context


def nl2br(value: str) -> Markup:
    """Convert newlines to <br> tags, escaping HTML first."""
    escaped = html_escape(str(value))
    return Markup(escaped.replace("\n", "<br>"))


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Load models once at startup."""
    index, mapping, embed_model, cross_encoder = _load_pipeline()
    pipeline["index"] = index
    pipeline["mapping"] = mapping
    pipeline["embed_model"] = embed_model
    pipeline["cross_encoder"] = cross_encoder

    verse_idx: dict[tuple[str, str, str], int] = {}
    for i, entry in enumerate(mapping):
        key = (entry["book_title"], entry["chapter"], entry["verse"])
        verse_idx[key] = i
    pipeline["verse_index"] = verse_idx

    pipeline["loaded"] = True
    yield
    pipeline.clear()


app = FastAPI(title="RAG Bible", lifespan=lifespan)
templates.env.filters["nl2br"] = nl2br

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
    cleaned = sanitize_query(query)

    if not cleaned:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"message": "Veuillez saisir une question ou un mot-cle."},
        )

    try:
        results = _run_search(cleaned)
    except Exception:
        logger.exception("Search failed for query: %s", cleaned)
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"message": "Une erreur interne est survenue. Veuillez reessayer."},
        )

    relevant = [r for r in results if r["score"] >= config.RELEVANCE_THRESHOLD]

    if not relevant:
        return templates.TemplateResponse(
            request=request,
            name="no_results.html",
            context={"query": cleaned},
        )

    for r in relevant:
        r["label"] = get_score_label(r["score"])
        r["pct"] = int(r["score"] * 100)
        r["context_verses"] = get_verse_context(r, pipeline["mapping"], pipeline["verse_index"])

    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={"results": relevant, "query": cleaned},
    )
