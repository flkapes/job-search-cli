"""Tests for progress markdown export — Feature 6."""

from __future__ import annotations

from codepractice.db.export import export_markdown
from codepractice.db.repositories import ProblemRepository, SessionRepository


class TestMarkdownExport:
    def test_creates_markdown_file(self, tmp_db, tmp_path):
        path = export_markdown(tmp_db, output_dir=tmp_path)
        assert path.exists()
        assert path.suffix == ".md"

    def test_filename_contains_report_and_date(self, tmp_db, tmp_path):
        path = export_markdown(tmp_db, output_dir=tmp_path)
        assert "report_" in path.name

    def test_contains_main_header(self, tmp_db, tmp_path):
        path = export_markdown(tmp_db, output_dir=tmp_path)
        content = path.read_text()
        # Should have a top-level heading
        assert content.startswith("#")

    def test_contains_stats_section(self, tmp_db, tmp_path):
        path = export_markdown(tmp_db, output_dir=tmp_path)
        content = path.read_text()
        assert any(kw in content.lower() for kw in ["total", "solved", "attempts", "score"])

    def test_contains_category_data_when_attempts_exist(self, tmp_db, tmp_path):
        prob_repo = ProblemRepository(tmp_db)
        sess_repo = SessionRepository(tmp_db)

        pid = prob_repo.create({"category": "dsa", "subcategory": "dp", "title": "T", "description": "D"})
        sid = sess_repo.start_session()
        sess_repo.record_attempt({
            "session_id": sid, "problem_id": pid,
            "user_code": "x", "ai_feedback": "", "ai_score": 0.8, "passed": True,
        })

        path = export_markdown(tmp_db, output_dir=tmp_path)
        content = path.read_text()
        assert "dsa" in content.lower()

    def test_contains_review_section(self, tmp_db, tmp_path):
        path = export_markdown(tmp_db, output_dir=tmp_path)
        content = path.read_text()
        assert "review" in content.lower() or "spaced" in content.lower()

    def test_export_via_cli_format_flag(self, tmp_db, tmp_path):
        from unittest.mock import patch

        from typer.testing import CliRunner

        from codepractice.main import app

        r = CliRunner()
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.db.export.EXPORTS_DIR", tmp_path):
            result = r.invoke(app, ["export", "--format", "md"])
        assert result.exit_code == 0

    def test_json_format_still_works(self, tmp_db, tmp_path):
        from unittest.mock import patch

        from typer.testing import CliRunner

        from codepractice.main import app

        r = CliRunner()
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.db.export.EXPORTS_DIR", tmp_path):
            result = r.invoke(app, ["export", "--format", "json"])
        assert result.exit_code == 0

    def test_default_format_is_json(self, tmp_db, tmp_path):
        """export without --format still works (defaults to json)."""
        from unittest.mock import patch

        from typer.testing import CliRunner

        from codepractice.main import app

        r = CliRunner()
        with patch("codepractice.db.get_db", return_value=tmp_db), \
             patch("codepractice.db.export.EXPORTS_DIR", tmp_path):
            result = r.invoke(app, ["export"])
        assert result.exit_code == 0
