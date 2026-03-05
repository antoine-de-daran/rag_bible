"""Unit tests for per-verse feedback (module + endpoint)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestRecordFeedback:
    """Tests for rag.feedback.record_feedback."""

    def setup_method(self) -> None:
        """Clear dedup state between tests."""
        import rag.feedback as fb

        fb._seen.clear()

    def test_appends_to_buffer(self, tmp_path: Path) -> None:
        from rag.feedback import record_feedback

        buf = tmp_path / "fb.jsonl"
        record_feedback(
            query="amour",
            book_title="Jean",
            chapter="3",
            verse="16",
            score=0.92,
            feedback="up",
            buffer_path=buf,
            flush_threshold=100,
            hf_repo="fake/repo",
        )
        lines = buf.read_text().strip().split("\n")
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["query"] == "amour"
        assert rec["feedback"] == "up"
        assert rec["source"] == "local"
        assert rec["session_id"] == ""
        assert "timestamp" in rec

    def test_multiple_records(self, tmp_path: Path) -> None:
        from rag.feedback import record_feedback

        buf = tmp_path / "fb.jsonl"
        for i in range(3):
            record_feedback(
                query=f"q{i}",
                book_title="Gen",
                chapter="1",
                verse=str(i),
                score=0.5,
                feedback="down",
                buffer_path=buf,
                flush_threshold=100,
                hf_repo="fake/repo",
            )
        lines = buf.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_flush_triggered_at_threshold(self, tmp_path: Path) -> None:
        from rag.feedback import record_feedback

        buf = tmp_path / "fb.jsonl"
        with patch("rag.feedback._flush_to_hub") as mock_flush:
            for i in range(5):
                record_feedback(
                    query=f"q{i}",
                    book_title="Gen",
                    chapter="1",
                    verse=str(i),
                    score=0.5,
                    feedback="up",
                    buffer_path=buf,
                    flush_threshold=5,
                    hf_repo="fake/repo",
                    source="production",
                )
            mock_flush.assert_called_once_with(buf, "fake/repo")

    def test_flush_not_triggered_for_local(self, tmp_path: Path) -> None:
        from rag.feedback import record_feedback

        buf = tmp_path / "fb.jsonl"
        with patch("rag.feedback._flush_to_hub") as mock_flush:
            for i in range(10):
                record_feedback(
                    query=f"q{i}",
                    book_title="Gen",
                    chapter="1",
                    verse=str(i),
                    score=0.5,
                    feedback="up",
                    buffer_path=buf,
                    flush_threshold=5,
                    hf_repo="fake/repo",
                    source="local",
                )
            mock_flush.assert_not_called()

    def test_cancel_record_in_buffer(self, tmp_path: Path) -> None:
        from rag.feedback import record_feedback

        buf = tmp_path / "fb.jsonl"
        record_feedback(
            query="amour",
            book_title="Jean",
            chapter="3",
            verse="16",
            score=0.92,
            feedback="cancel_up",
            buffer_path=buf,
            flush_threshold=100,
            hf_repo="fake/repo",
        )
        rec = json.loads(buf.read_text().strip())
        assert rec["feedback"] == "cancel_up"

    def test_session_id_in_record(self, tmp_path: Path) -> None:
        from rag.feedback import record_feedback

        buf = tmp_path / "fb.jsonl"
        record_feedback(
            query="test",
            book_title="Gen",
            chapter="1",
            verse="1",
            score=0.5,
            feedback="up",
            buffer_path=buf,
            flush_threshold=100,
            hf_repo="fake/repo",
            session_id="abc-123-uuid",
        )
        rec = json.loads(buf.read_text().strip())
        assert rec["session_id"] == "abc-123-uuid"

    def test_source_field_in_record(self, tmp_path: Path) -> None:
        from rag.feedback import record_feedback

        buf = tmp_path / "fb.jsonl"
        record_feedback(
            query="test",
            book_title="Gen",
            chapter="1",
            verse="1",
            score=0.5,
            feedback="up",
            buffer_path=buf,
            flush_threshold=100,
            hf_repo="fake/repo",
            source="production",
        )
        rec = json.loads(buf.read_text().strip())
        assert rec["source"] == "production"


@pytest.mark.unit
class TestFeedbackDedup:
    """Tests for duplicate feedback suppression."""

    def setup_method(self) -> None:
        """Clear dedup state between tests."""
        import rag.feedback as fb

        fb._seen.clear()

    def test_duplicate_feedback_skipped(self, tmp_path: Path) -> None:
        from rag.feedback import record_feedback

        buf = tmp_path / "fb.jsonl"
        kwargs = dict(
            query="amour",
            book_title="Jean",
            chapter="3",
            verse="16",
            score=0.92,
            feedback="down",
            buffer_path=buf,
            flush_threshold=100,
            hf_repo="fake/repo",
            session_id="sess-1",
        )
        record_feedback(**kwargs)
        record_feedback(**kwargs)
        lines = buf.read_text().strip().split("\n")
        assert len(lines) == 1

    def test_cancel_clears_dedup_state(self, tmp_path: Path) -> None:
        from rag.feedback import record_feedback

        buf = tmp_path / "fb.jsonl"
        base = dict(
            query="amour",
            book_title="Jean",
            chapter="3",
            verse="16",
            score=0.92,
            buffer_path=buf,
            flush_threshold=100,
            hf_repo="fake/repo",
            session_id="sess-1",
        )
        record_feedback(**base, feedback="up")
        record_feedback(**base, feedback="cancel_up")
        record_feedback(**base, feedback="up")
        lines = buf.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_direction_change_allowed(self, tmp_path: Path) -> None:
        from rag.feedback import record_feedback

        buf = tmp_path / "fb.jsonl"
        base = dict(
            query="amour",
            book_title="Jean",
            chapter="3",
            verse="16",
            score=0.92,
            buffer_path=buf,
            flush_threshold=100,
            hf_repo="fake/repo",
            session_id="sess-1",
        )
        record_feedback(**base, feedback="up")
        record_feedback(**base, feedback="down")
        lines = buf.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["feedback"] == "up"
        assert json.loads(lines[1])["feedback"] == "down"


@pytest.mark.unit
class TestFeedbackEndpoint:
    """Tests for POST /feedback."""

    def test_valid_up_returns_204(self, client: TestClient) -> None:
        with patch("app.record_feedback"):
            resp = client.post(
                "/feedback",
                data={
                    "query": "amour",
                    "book_title": "Jean",
                    "chapter": "3",
                    "verse": "16",
                    "score": "0.92",
                    "feedback": "up",
                },
            )
        assert resp.status_code == 204

    def test_valid_down_returns_204(self, client: TestClient) -> None:
        with patch("app.record_feedback"):
            resp = client.post(
                "/feedback",
                data={"feedback": "down"},
            )
        assert resp.status_code == 204

    def test_cancel_up_returns_204(self, client: TestClient) -> None:
        with patch("app.record_feedback"):
            resp = client.post(
                "/feedback",
                data={"feedback": "cancel_up"},
            )
        assert resp.status_code == 204

    def test_cancel_down_returns_204(self, client: TestClient) -> None:
        with patch("app.record_feedback"):
            resp = client.post(
                "/feedback",
                data={"feedback": "cancel_down"},
            )
        assert resp.status_code == 204

    def test_invalid_feedback_returns_400(self, client: TestClient) -> None:
        resp = client.post(
            "/feedback",
            data={"feedback": "maybe"},
        )
        assert resp.status_code == 400

    def test_missing_feedback_returns_400(self, client: TestClient) -> None:
        resp = client.post("/feedback", data={})
        assert resp.status_code == 400

    def test_storage_error_still_204(self, client: TestClient) -> None:
        with patch(
            "app.record_feedback",
            side_effect=OSError("disk full"),
        ):
            resp = client.post(
                "/feedback",
                data={"feedback": "up"},
            )
        assert resp.status_code == 204


@pytest.mark.unit
class TestResultsHtmlFeedback:
    """Verify feedback buttons appear in search results."""

    def test_feedback_buttons_in_results(self, client: TestClient) -> None:
        resp = client.post("/search", data={"query": "amour de Dieu"})
        assert resp.status_code == 200
        html = resp.text
        assert 'class="feedback-btn feedback-up"' in html
        assert 'class="feedback-btn feedback-down"' in html
        assert 'data-feedback="up"' in html
        assert 'data-feedback="down"' in html

    def test_data_attributes_on_card(self, client: TestClient) -> None:
        resp = client.post("/search", data={"query": "amour de Dieu"})
        html = resp.text
        assert 'data-query="amour de Dieu"' in html
        assert "data-score=" in html
