"""Tests for the static problem bank loader."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from codepractice.core.problem_bank import get_problems_for_category, load_all_problems


class TestLoadAllProblems:
    def test_loads_bundled_problems(self):
        """The package ships with problem JSON files; at least one should load."""
        problems = load_all_problems()
        assert isinstance(problems, list)
        assert len(problems) > 0

    def test_each_problem_has_required_fields(self):
        problems = load_all_problems()
        for p in problems:
            assert "title" in p, f"Missing 'title' in {p}"
            assert "description" in p, f"Missing 'description' in {p}"
            assert "category" in p, f"Missing 'category' in {p}"

    def test_problems_have_valid_difficulty(self):
        problems = load_all_problems()
        valid = {"easy", "medium", "hard"}
        for p in problems:
            diff = p.get("difficulty", "medium")
            assert diff in valid, f"Invalid difficulty '{diff}' for problem '{p.get('title')}'"

    def test_dsa_problems_exist(self):
        problems = load_all_problems()
        dsa = [p for p in problems if p.get("category") == "dsa"]
        assert len(dsa) > 0

    def test_python_fundamentals_exist(self):
        problems = load_all_problems()
        python = [p for p in problems if p.get("category") == "python_fundamentals"]
        assert len(python) > 0

    def test_nonexistent_dir_returns_empty(self):
        with patch("codepractice.core.problem_bank.PROBLEMS_DATA_DIR", Path("/nonexistent/path")):
            problems = load_all_problems()
        assert problems == []

    def test_handles_invalid_json_gracefully(self, tmp_path):
        """Corrupt JSON files should be skipped, not crash."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ not valid json }")
        good_file = tmp_path / "good.json"
        good_file.write_text(json.dumps([
            {"title": "T", "description": "D", "category": "dsa", "difficulty": "easy"}
        ]))
        with patch("codepractice.core.problem_bank.PROBLEMS_DATA_DIR", tmp_path):
            problems = load_all_problems()
        assert len(problems) == 1
        assert problems[0]["title"] == "T"

    def test_handles_problems_key_format(self, tmp_path):
        """Some JSON files wrap problems in a 'problems' key."""
        wrapped = tmp_path / "wrapped.json"
        wrapped.write_text(json.dumps({"problems": [
            {"title": "W", "description": "D", "category": "dsa", "difficulty": "medium"}
        ]}))
        with patch("codepractice.core.problem_bank.PROBLEMS_DATA_DIR", tmp_path):
            problems = load_all_problems()
        assert len(problems) == 1
        assert problems[0]["title"] == "W"


class TestGetProblemsForCategory:
    def test_filter_by_category(self):
        problems = get_problems_for_category("dsa")
        assert all(p.get("category") == "dsa" for p in problems)

    def test_filter_by_category_and_subcategory(self):
        problems = get_problems_for_category("dsa", subcategory="two_pointers")
        assert all(
            p.get("category") == "dsa" and p.get("subcategory") == "two_pointers"
            for p in problems
        )

    def test_nonexistent_category_returns_empty(self):
        problems = get_problems_for_category("nonexistent_category_xyz")
        assert problems == []

    def test_python_fundamentals_filter(self):
        problems = get_problems_for_category("python_fundamentals")
        assert len(problems) > 0
        assert all(p.get("category") == "python_fundamentals" for p in problems)
