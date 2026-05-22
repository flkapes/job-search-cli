from __future__ import annotations

from types import SimpleNamespace

from codepractice.tui.screens.practice import PracticeContent


class _FakeRepo:
    def __init__(self):
        self.kwargs = None

    def get_random(self, **kwargs):
        self.kwargs = kwargs
        return {
            "id": 1,
            "title": "Coin Change",
            "description": "desc",
            "category": "dsa",
            "subcategory": "dynamic_programming",
            "difficulty": "medium",
            "examples": [],
            "hints": [],
            "solution": None,
            "tags": [],
        }


def test_load_next_problem_propagates_subcategory(monkeypatch):
    widget = PracticeContent()
    repo = _FakeRepo()
    fake_app = SimpleNamespace(problem_repo=repo)
    monkeypatch.setattr(PracticeContent, "app", property(lambda self: fake_app))

    monkeypatch.setattr(widget, "_show_phase", lambda phase: None)
    monkeypatch.setattr(widget, "_show_problem", lambda: None)

    widget._load_next_problem(category="dsa", subcategory="dynamic_programming")

    assert repo.kwargs == {
        "category": "dsa",
        "subcategory": "dynamic_programming",
        "difficulty": None,
    }
