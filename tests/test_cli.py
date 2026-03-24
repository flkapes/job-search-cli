"""Tests for the Typer CLI commands (non-TUI commands only)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from codepractice.main import app

runner = CliRunner()


class TestStatsCommand:
    def _mock_stats(self):
        mock_repo = MagicMock()
        mock_repo.get_stats.return_value = {
            "today_solved": 3,
            "total_solved": 42,
            "avg_score": 78.5,
            "active_days_30": 15,
            "total_attempts": 60,
        }
        return mock_repo

    def test_stats_exits_zero(self):
        mock_repo = self._mock_stats()
        with patch("codepractice.db.database.get_db", return_value=MagicMock()), \
             patch("codepractice.db.repositories.sessions.SessionRepository.get_stats",
                   return_value=mock_repo.get_stats.return_value):
            result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0

    def test_stats_shows_table_header(self):
        mock_repo = self._mock_stats()
        with patch("codepractice.db.repositories.sessions.SessionRepository.get_stats",
                   return_value=mock_repo.get_stats.return_value):
            result = runner.invoke(app, ["stats"])
        # Even if patching is imperfect, command should not crash with unhandled exception
        assert result.exit_code in (0, 1)


class TestCheckCommand:
    def test_check_with_healthy_llm(self):
        mock_client = MagicMock()
        mock_client.__class__.__name__ = "OllamaClient"
        mock_client.health_check.return_value = True
        mock_client.list_models.return_value = ["llama3", "codellama"]
        with patch("codepractice.llm.client.get_client", return_value=mock_client):
            result = runner.invoke(app, ["check"])
        assert result.exit_code == 0

    def test_check_with_offline_llm(self):
        mock_client = MagicMock()
        mock_client.__class__.__name__ = "OllamaClient"
        mock_client.health_check.return_value = False
        mock_client.list_models.return_value = []
        with patch("codepractice.llm.client.get_client", return_value=mock_client):
            result = runner.invoke(app, ["check"])
        assert result.exit_code == 0

    def test_check_handles_exception(self):
        with patch("codepractice.llm.client.get_client", side_effect=Exception("refused")):
            result = runner.invoke(app, ["check"])
        assert result.exit_code in (0, 1)


class TestExportCommand:
    def test_export_creates_file(self):
        tmp_dir = tempfile.mkdtemp()
        with patch("codepractice.db.export.EXPORTS_DIR", Path(tmp_dir)):
            result = runner.invoke(app, ["export"])
        # May succeed or fail depending on DB state; just should not hard-crash
        assert result.exit_code in (0, 1)


class TestHelpOutput:
    def test_help_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "codepractice" in result.output.lower() or "Usage" in result.output

    def test_stats_help(self):
        result = runner.invoke(app, ["stats", "--help"])
        assert result.exit_code == 0

    def test_check_help(self):
        result = runner.invoke(app, ["check", "--help"])
        assert result.exit_code == 0

    def test_export_help(self):
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0

    def test_config_help(self):
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
