"""My Library — bookmarked problems with saved solutions and comparison view."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, Select, Static

from codepractice.core.models import Problem
from codepractice.utils.text_utils import difficulty_badge

CATEGORY_OPTIONS = [
    ("All categories", ""),
    ("Python Fundamentals", "python_fundamentals"),
    ("DSA", "dsa"),
    ("Practical", "practical"),
    ("Custom", "custom"),
]

DIFFICULTY_OPTIONS = [
    ("All difficulties", ""),
    ("Easy", "easy"),
    ("Medium", "medium"),
    ("Hard", "hard"),
]


class SolutionCompareModal(ModalScreen):
    """Side-by-side: the user's best solution vs the AI-optimal solution."""

    DEFAULT_CSS = """
    SolutionCompareModal {
        align: center middle;
    }

    SolutionCompareModal #compare-container {
        width: 92%;
        height: 88%;
        background: #161b22;
        border: solid #58a6ff;
        padding: 1;
    }

    SolutionCompareModal #compare-header {
        height: auto;
        background: #1c2128;
        border-bottom: solid #30363d;
        padding: 0 2;
    }

    SolutionCompareModal #compare-body {
        height: 1fr;
    }

    SolutionCompareModal #compare-user {
        width: 1fr;
        border-right: solid #30363d;
        padding: 1;
    }

    SolutionCompareModal #compare-ai {
        width: 1fr;
        padding: 1;
    }

    SolutionCompareModal #compare-close-bar {
        height: 3;
        border-top: solid #30363d;
        padding: 0 2;
        dock: bottom;
    }
    """

    def __init__(self, problem: Problem, best_attempt: dict | None, **kwargs):
        super().__init__(**kwargs)
        self._problem = problem
        self._attempt = best_attempt

    def compose(self) -> ComposeResult:
        problem = self._problem
        attempt = self._attempt or {}
        badge = difficulty_badge(
            problem.difficulty.value if hasattr(problem.difficulty, "value") else problem.difficulty
        )
        score = attempt.get("ai_score")
        score_str = f"  Your best score: [cyan]{score * 100:.0f}%[/cyan]" if score is not None else ""

        with Vertical(id="compare-container"):
            with Horizontal(id="compare-header"):
                yield Label(f"[bold]{problem.title}[/bold]  {badge}{score_str}")
            with Horizontal(id="compare-body"):
                with VerticalScroll(id="compare-user"):
                    yield Label("[bold #58a6ff]Your Solution[/bold #58a6ff]")
                    yield Static(
                        attempt.get("user_code") or "[dim]No attempt recorded yet.[/dim]",
                        id="user-solution",
                    )
                with VerticalScroll(id="compare-ai"):
                    yield Label("[bold #bc8cff]AI-Optimal Solution[/bold #bc8cff]")
                    if problem.solution and problem.solution.code:
                        yield Static(problem.solution.code, id="ai-solution")
                        meta = (
                            f"\n[dim]Time: {problem.solution.time_complexity}  "
                            f"Space: {problem.solution.space_complexity}[/dim]"
                        )
                        if problem.solution.explanation:
                            meta += f"\n\n{problem.solution.explanation}"
                        yield Static(meta, id="ai-solution-meta")
                    else:
                        yield Static("[dim]No reference solution stored.[/dim]", id="ai-solution")
            with Horizontal(id="compare-close-bar"):
                yield Button("Close [Escape]", id="btn-close-compare", classes="secondary-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-compare":
            self.dismiss()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()


class LibraryContent(Widget):
    """Bookmarked problems with filters and solution comparison."""

    DEFAULT_CSS = """
    LibraryContent {
        height: 1fr;
        padding: 0 1;
    }

    LibraryContent #library-filters {
        height: 3;
        margin: 1 0;
    }

    LibraryContent #library-filters Select {
        width: 30;
        margin-right: 2;
    }

    LibraryContent #library-table {
        height: 1fr;
    }
    """

    _row_problem_ids: list[int | None] = []

    def compose(self) -> ComposeResult:
        yield Label("[bold #58a6ff]📚 My Library[/bold #58a6ff]")
        yield Static(
            "[#8b949e]Bookmark problems with [bold]B[/bold] during practice. "
            "Select a row to compare your solution with the AI-optimal one.[/#8b949e]"
        )
        with Horizontal(id="library-filters"):
            yield Select(
                [(label, value) for label, value in CATEGORY_OPTIONS],
                value="",
                id="filter-category",
                allow_blank=False,
            )
            yield Select(
                [(label, value) for label, value in DIFFICULTY_OPTIONS],
                value="",
                id="filter-difficulty",
                allow_blank=False,
            )
        yield DataTable(id="library-table")

    def on_mount(self) -> None:
        table = self.query_one("#library-table", DataTable)
        table.cursor_type = "row"
        self._load_table()

    def _current_filters(self) -> tuple[str | None, str | None]:
        try:
            category = self.query_one("#filter-category", Select).value or None
            difficulty = self.query_one("#filter-difficulty", Select).value or None
            return category, difficulty
        except Exception:
            return None, None

    def _load_table(self) -> None:
        table = self.query_one("#library-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Title", "Category", "Difficulty", "Tags", "Best Score", "Solved")
        self._row_problem_ids = []

        category, difficulty = self._current_filters()
        try:
            problems = self.app.problem_repo.get_bookmarked(category=category, difficulty=difficulty)
        except Exception:
            problems = []

        for p in problems:
            best = None
            try:
                best = self.app.session_repo.get_best_attempt_for_problem(p["id"])
            except Exception:
                pass
            score = f"{best['ai_score'] * 100:.0f}%" if best and best.get("ai_score") is not None else "—"
            solved = "✓" if p.get("times_solved", 0) > 0 else "—"
            tags = ", ".join((p.get("tags") or [])[:3])
            self._row_problem_ids.append(p["id"])
            table.add_row(
                p.get("title", "?")[:48],
                p.get("category", "—"),
                p.get("difficulty", "—"),
                tags or "—",
                score,
                solved,
            )

        if not problems:
            self._row_problem_ids.append(None)
            table.add_row("No bookmarks yet — press B on any problem", "—", "—", "—", "—", "—")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in ("filter-category", "filter-difficulty"):
            self._load_table()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "library-table":
            return
        row = event.cursor_row
        if row < 0 or row >= len(self._row_problem_ids):
            return
        problem_id = self._row_problem_ids[row]
        if not problem_id:
            return
        try:
            data = self.app.problem_repo.get_by_id(problem_id)
            if not data:
                return
            problem = Problem.from_db(data)
            best = self.app.session_repo.get_best_attempt_for_problem(problem_id)
            self.app.push_screen(SolutionCompareModal(problem, best))
        except Exception:
            self.notify("Could not open the comparison view.", severity="error")
