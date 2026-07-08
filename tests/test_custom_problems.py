"""Tests for custom problem creation, validation, and export/import."""

from __future__ import annotations

import json

import pytest

from codepractice.core.custom_problems import (
    build_custom_problem,
    export_custom_problems,
    import_custom_problems,
)
from codepractice.db.repositories import ProblemRepository


class TestBuildCustomProblem:
    def test_minimal_valid(self):
        p = build_custom_problem(title="T", description="d")
        assert p.source.value == "custom"
        assert p.title == "T"
        assert p.difficulty.value == "medium"

    def test_title_required(self):
        with pytest.raises(ValueError, match="Title"):
            build_custom_problem(title="  ", description="d")

    def test_description_required(self):
        with pytest.raises(ValueError, match="Description"):
            build_custom_problem(title="T", description="")

    def test_invalid_difficulty_rejected(self):
        with pytest.raises(ValueError, match="difficulty"):
            build_custom_problem(title="T", description="d", difficulty="brutal")

    def test_empty_examples_dropped(self):
        p = build_custom_problem(
            title="T", description="d",
            examples=[{"input": "1", "output": "2"}, {"input": "", "output": ""}],
        )
        assert len(p.examples) == 1

    def test_hints_and_tags_cleaned(self):
        p = build_custom_problem(
            title="T", description="d",
            hints=["  first ", "", "second"],
            tags=[" a", "", "b "],
        )
        assert p.hints == ["first", "second"]
        assert p.tags == ["a", "b"]

    def test_solution_only_when_code_given(self):
        assert build_custom_problem(title="T", description="d").solution is None
        p = build_custom_problem(title="T", description="d", solution_code="x = 1")
        assert p.solution.code == "x = 1"


class TestPersistence:
    def test_custom_problem_saved_and_in_random_pool(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        p = build_custom_problem(title="Custom One", description="d", category="dsa")
        repo.create(p.to_db())
        row = repo.get_random()
        assert row["title"] == "Custom One"
        assert row["source"] == "custom"

    def test_get_by_source(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        repo.create(build_custom_problem(title="A", description="d").to_db())
        repo.create({"category": "dsa", "title": "B", "description": "d"})  # static
        customs = repo.get_by_source("custom")
        assert [c["title"] for c in customs] == ["A"]


class TestExportImport:
    def _seed(self, repo):
        p = build_custom_problem(
            title="Exportable", description="desc",
            examples=[{"input": "1", "output": "2"}],
            hints=["h1"], solution_code="print(2)", tags=["io"],
        )
        repo.create(p.to_db())

    def test_export_writes_file(self, tmp_db, tmp_path):
        repo = ProblemRepository(tmp_db)
        self._seed(repo)
        out = tmp_path / "problems.json"
        count = export_custom_problems(repo, out)
        assert count == 1
        data = json.loads(out.read_text())
        assert data["problems"][0]["title"] == "Exportable"
        assert data["problems"][0]["examples"][0]["output"] == "2"

    def test_export_empty(self, tmp_db, tmp_path):
        repo = ProblemRepository(tmp_db)
        out = tmp_path / "problems.json"
        assert export_custom_problems(repo, out) == 0

    def test_roundtrip_import(self, tmp_db, tmp_path):
        repo = ProblemRepository(tmp_db)
        self._seed(repo)
        out = tmp_path / "problems.json"
        export_custom_problems(repo, out)

        # Import into a fresh DB
        import tempfile
        from pathlib import Path

        from codepractice.db.database import DatabaseManager
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db2_path = Path(f.name)
        try:
            repo2 = ProblemRepository(DatabaseManager(db2_path))
            assert import_custom_problems(repo2, out) == 1
            imported = repo2.get_by_source("custom")[0]
            assert imported["title"] == "Exportable"
            assert imported["hints"] == ["h1"]
            assert imported["solution"]["code"] == "print(2)"
        finally:
            db2_path.unlink(missing_ok=True)

    def test_import_skips_duplicates(self, tmp_db, tmp_path):
        repo = ProblemRepository(tmp_db)
        self._seed(repo)
        out = tmp_path / "problems.json"
        export_custom_problems(repo, out)
        assert import_custom_problems(repo, out) == 0  # same title already present

    def test_import_skips_invalid_entries(self, tmp_db, tmp_path):
        repo = ProblemRepository(tmp_db)
        payload = {"problems": [
            {"title": "", "description": "missing title"},
            {"title": "Good", "description": "ok"},
            "not-a-dict",
        ]}
        f = tmp_path / "mixed.json"
        f.write_text(json.dumps(payload))
        assert import_custom_problems(repo, f) == 1

    def test_import_rejects_non_list(self, tmp_db, tmp_path):
        repo = ProblemRepository(tmp_db)
        f = tmp_path / "bad.json"
        f.write_text('{"problems": {"nope": 1}}')
        with pytest.raises(ValueError):
            import_custom_problems(repo, f)


class TestScreen:
    def test_create_problem_screen_imports(self):
        from codepractice.tui.screens.create_problem import CreateProblemContent
        assert CreateProblemContent is not None
