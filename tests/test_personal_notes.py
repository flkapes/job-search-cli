"""Tests for personal notes on problems — Feature 3."""

from __future__ import annotations

from codepractice.db.repositories import ProblemRepository


class TestPersonalNotes:
    def test_save_and_get_note(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        pid = repo.create({"category": "dsa", "title": "Two Sum", "description": "Find pair"})

        repo.save_note(pid, "Remember: use a hash map!")
        assert repo.get_note(pid) == "Remember: use a hash map!"

    def test_note_empty_by_default(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        pid = repo.create({"category": "dsa", "title": "New", "description": "D"})
        assert repo.get_note(pid) == ""

    def test_update_overwrites_existing_note(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        pid = repo.create({"category": "dsa", "title": "P", "description": "D"})

        repo.save_note(pid, "First note")
        repo.save_note(pid, "Updated note")
        assert repo.get_note(pid) == "Updated note"

    def test_note_returned_in_get_by_id(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        pid = repo.create({"category": "dsa", "title": "P", "description": "D"})
        repo.save_note(pid, "My insight")

        problem = repo.get_by_id(pid)
        assert problem["user_notes"] == "My insight"

    def test_save_note_nonexistent_problem_is_noop(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        repo.save_note(99999, "ghost")  # should not raise

    def test_get_note_nonexistent_returns_empty(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        assert repo.get_note(99999) == ""

    def test_multiline_note_preserved(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        pid = repo.create({"category": "dsa", "title": "P", "description": "D"})
        note = "Line 1\nLine 2\n• Bullet point"
        repo.save_note(pid, note)
        assert repo.get_note(pid) == note

    def test_notes_are_per_problem(self, tmp_db):
        repo = ProblemRepository(tmp_db)
        p1 = repo.create({"category": "dsa", "title": "P1", "description": "D"})
        p2 = repo.create({"category": "dsa", "title": "P2", "description": "D"})

        repo.save_note(p1, "Note for P1")
        repo.save_note(p2, "Note for P2")

        assert repo.get_note(p1) == "Note for P1"
        assert repo.get_note(p2) == "Note for P2"
