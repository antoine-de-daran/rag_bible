"""Per-verse feedback buffer with periodic HuggingFace Dataset flush."""

import json
import logging
import threading
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_scheduler: threading.Timer | None = None
_count = 0
_SEEN_MAX_SIZE = 10_000
_seen: OrderedDict[tuple[str, ...], str] = OrderedDict()


def record_feedback(
    query: str,
    book_title: str,
    chapter: str,
    verse: str,
    score: float,
    feedback: str,
    buffer_path: Path,
    flush_threshold: int,
    hf_repo: str,
    source: str = "local",
    session_id: str = "",
) -> None:
    """Append a feedback record to the local JSONL buffer.

    Parameters
    ----------
    query : str
        The search query that produced the result.
    book_title : str
        Book title of the rated verse.
    chapter : str
        Chapter number.
    verse : str
        Verse number.
    score : float
        Relevance score of the result.
    feedback : str
        Either "up" or "down".
    buffer_path : Path
        Path to the JSONL buffer file.
    flush_threshold : int
        Number of records that triggers an automatic flush.
    hf_repo : str
        HuggingFace Dataset repo ID for flushing.
    source : str
        Environment source tag ("production" or "local").
    session_id : str
        Browser session identifier (UUID from client).
    """
    global _count  # noqa: PLW0603

    dedup_key = (session_id, query, book_title, chapter, verse)

    with _lock:
        if feedback in ("up", "down"):
            if _seen.get(dedup_key) == feedback:
                return
            _seen[dedup_key] = feedback
            _seen.move_to_end(dedup_key)
            if len(_seen) > _SEEN_MAX_SIZE:
                _seen.popitem(last=False)
        elif feedback.startswith("cancel_"):
            _seen.pop(dedup_key, None)

        record = {
            "query": query,
            "book_title": book_title,
            "chapter": chapter,
            "verse": verse,
            "score": score,
            "feedback": feedback,
            "source": source,
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        buffer_path.parent.mkdir(parents=True, exist_ok=True)
        with open(buffer_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        _count += 1

        if _count >= flush_threshold and source == "production":
            _count = 0
            threading.Thread(
                target=_flush_to_hub,
                args=(buffer_path, hf_repo),
                daemon=True,
            ).start()


def _flush_to_hub(buffer_path: Path, hf_repo: str) -> None:
    """Upload buffer file to HF Dataset repo, then truncate it.

    Parameters
    ----------
    buffer_path : Path
        Path to the JSONL buffer file.
    hf_repo : str
        HuggingFace Dataset repo ID.
    """
    try:
        with _lock:
            if not buffer_path.exists() or buffer_path.stat().st_size == 0:
                return
            data = buffer_path.read_bytes()

        from huggingface_hub import HfApi

        api = HfApi()
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        api.upload_file(
            path_or_fileobj=data,
            path_in_repo=f"data/feedback_{ts}.jsonl",
            repo_id=hf_repo,
            repo_type="dataset",
        )

        with _lock:
            # Remove only the bytes we successfully uploaded;
            # new records appended during upload are preserved.
            current = buffer_path.read_bytes()
            if current.startswith(data):
                buffer_path.write_bytes(current[len(data) :])
            else:
                buffer_path.write_text("")

        global _count  # noqa: PLW0603
        _count = 0
        logger.info("Flushed feedback to %s", hf_repo)
    except Exception:
        logger.exception("Failed to flush feedback to HF Hub")


def start_flush_scheduler(
    buffer_path: Path,
    hf_repo: str,
    interval_s: int,
) -> None:
    """Start a recurring daemon timer that flushes the buffer.

    Parameters
    ----------
    buffer_path : Path
        Path to the JSONL buffer file.
    hf_repo : str
        HuggingFace Dataset repo ID.
    interval_s : int
        Seconds between flush attempts.
    """
    global _scheduler  # noqa: PLW0603

    def _tick() -> None:
        _flush_to_hub(buffer_path, hf_repo)
        start_flush_scheduler(buffer_path, hf_repo, interval_s)

    _scheduler = threading.Timer(interval_s, _tick)
    _scheduler.daemon = True
    _scheduler.start()


def stop_flush_scheduler() -> None:
    """Cancel the recurring flush timer."""
    global _scheduler  # noqa: PLW0603
    if _scheduler is not None:
        _scheduler.cancel()
        _scheduler = None


def flush_remaining(buffer_path: Path, hf_repo: str) -> None:
    """Flush remaining buffer on shutdown (best-effort, never raises).

    Parameters
    ----------
    buffer_path : Path
        Path to the JSONL buffer file.
    hf_repo : str
        HuggingFace Dataset repo ID.
    """
    try:
        _flush_to_hub(buffer_path, hf_repo)
    except Exception:
        logger.exception("Final feedback flush failed")
