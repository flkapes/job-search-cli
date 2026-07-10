"""Tests for problem bookmarking and the solution library data layer."""

from __future__ import annotations

from codepractice.db.repositories import ProblemRepository, SessionRepository


def _make_problem(repo: ProblemRepository, title="P", category="dsa", difficulty="medium", tags=None) -> int:
    return repo.create({
        "category": category,
        "title": title,
        "description": "d",
        "difficulty": difficulty,
        "tags": tags or [],
    })


class TestBookmarkToggle:
    def test_new_problem_not_bookmarked(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        pid = _make_problem(repo)
        assert repo.is_bookmarked(pid) is False

    def test_set_and_unset(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        pid = _make_problem(repo)
        repo.set_bookmark(pid, True)
        assert repo.is_bookmarked(pid) is True
        repo.set_bookmark(pid, False)
        assert repo.is_bookmarked(pid) is False


class TestGetBookmarked:
    def test_only_bookmarked_returned(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        a = _make_problem(repo, "A")
        _make_problem(repo, "B")
        repo.set_bookmark(a, True)
        results = repo.get_bookmarked()
        assert [r["id"] for r in results] == [a]

    def test_category_filter(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        a = _make_problem(repo, "A", category="dsa")
        b = _make_problem(repo, "B", category="python_fundamentals")
        repo.set_bookmark(a, True)
        repo.set_bookmark(b, True)
        results = repo.get_bookmarked(category="python_fundamentals")
        assert [r["id"] for r in results] == [b]

    def test_difficulty_filter(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        a = _make_problem(repo, "A", difficulty="easy")
        b = _make_problem(repo, "B", difficulty="hard")
        repo.set_bookmark(a, True)
        repo.set_bookmark(b, True)
        results = repo.get_bookmarked(difficulty="hard")
        assert [r["id"] for r in results] == [b]

    def test_tag_filter(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        a = _make_problem(repo, "A", tags=["arrays", "sorting"])
        b = _make_problem(repo, "B", tags=["graphs"])
        repo.set_bookmark(a, True)
        repo.set_bookmark(b, True)
        results = repo.get_bookmarked(tag="graphs")
        assert [r["id"] for r in results] == [b]

    def test_rows_parsed_with_json_fields(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        a = _make_problem(repo, "A", tags=["x"])
        repo.set_bookmark(a, True)
        row = repo.get_bookmarked()[0]
        assert row["tags"] == ["x"]


class TestBestAttempt:
    def test_none_when_no_attempts(self, tmp_db):
        sessions = SessionRepository(tmp_db)
        assert sessions.get_best_attempt_for_problem(1) is None

    def test_highest_score_wins(self, tmp_db):
        problems = ProblemRepository(tmp_db)
        sessions = SessionRepository(tmp_db)
        pid = _make_problem(problems)
        sid = sessions.start_session("free")
        sessions.record_attempt({"session_id": sid, "problem_id": pid,
                                 "user_code": "v1", "ai_score": 0.4, "passed": False})
        sessions.record_attempt({"session_id": sid, "problem_id": pid,
                                 "user_code": "v2", "ai_score": 0.9, "passed": True})
        best = sessions.get_best_attempt_for_problem(pid)
        assert best["user_code"] == "v2"

    def test_empty_code_attempts_ignored(self, tmp_db):
        problems = ProblemRepository(tmp_db)
        sessions = SessionRepository(tmp_db)
        pid = _make_problem(problems)
        sid = sessions.start_session("free")
        sessions.record_attempt({"session_id": sid, "problem_id": pid,
                                 "user_code": "", "ai_score": 1.0, "passed": True})
        assert sessions.get_best_attempt_for_problem(pid) is None


class TestLibraryScreen:
    def test_imports_and_composes(self):
        from codepractice.tui.screens.library import LibraryContent, SolutionCompareModal
        assert LibraryContent is not None
        assert SolutionCompareModal is not None

    def test_compare_modal_holds_problem_and_attempt(self):
        from codepractice.core.models import Problem
        from codepractice.tui.screens.library import SolutionCompareModal
        p = Problem(title="T", description="d")
        modal = SolutionCompareModal(p, {"user_code": "x = 1", "ai_score": 0.8})
        assert modal._problem.title == "T"
        assert modal._attempt["user_code"] == "x = 1"
