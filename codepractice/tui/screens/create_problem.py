"""New Problem form — author custom drill problems inside the TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static, TextArea

from codepractice.core.custom_problems import build_custom_problem

CATEGORY_OPTIONS = [
    ("Practical", "practical"),
    ("Python Fundamentals", "python_fundamentals"),
    ("DSA", "dsa"),
]

DIFFICULTY_OPTIONS = [("Easy", "easy"), ("Medium", "medium"), ("Hard", "hard")]


class CreateProblemContent(Widget):
    """Form for creating a custom problem stored with source='custom'."""

    DEFAULT_CSS = """
    CreateProblemContent {
        height: 1fr;
        padding: 0 1;
    }

    CreateProblemContent .field-label {
        color: #8b949e;
        margin-top: 1;
    }

    CreateProblemContent #cp-description,
    CreateProblemContent #cp-hints,
    CreateProblemContent #cp-solution {
        height: 6;
    }

    CreateProblemContent #cp-selects Select {
        width: 30;
        margin-right: 2;
    }

    CreateProblemContent .example-row Input {
        width: 1fr;
        margin-right: 1;
    }

    CreateProblemContent #cp-actions {
        height: 3;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("[bold #58a6ff]✏️ New Problem[/bold #58a6ff]")
            yield Static(
                "[#8b949e]Custom problems join random selection and the spaced-repetition "
                "review queue. Export them with [bold]codepractice export-problems[/bold].[/#8b949e]"
            )

            yield Label("Title *", classes="field-label")
            yield Input(placeholder="e.g. Parse a log file for error spikes", id="cp-title")

            with Horizontal(id="cp-selects"):
                yield Select(CATEGORY_OPTIONS, value="practical", id="cp-category", allow_blank=False)
                yield Select(DIFFICULTY_OPTIONS, value="medium", id="cp-difficulty", allow_blank=False)

            yield Label("Subcategory (optional)", classes="field-label")
            yield Input(placeholder="e.g. two_pointers, oop, parsing", id="cp-subcategory")

            yield Label("Description * (markdown supported)", classes="field-label")
            yield TextArea("", id="cp-description")

            yield Label("Example 1 — stdin input / expected stdout (optional)", classes="field-label")
            with Horizontal(classes="example-row"):
                yield Input(placeholder="input", id="cp-ex1-in")
                yield Input(placeholder="expected output", id="cp-ex1-out")

            yield Label("Example 2 (optional)", classes="field-label")
            with Horizontal(classes="example-row"):
                yield Input(placeholder="input", id="cp-ex2-in")
                yield Input(placeholder="expected output", id="cp-ex2-out")

            yield Label("Hints — one per line (optional)", classes="field-label")
            yield TextArea("", id="cp-hints")

            yield Label("Reference solution code (optional)", classes="field-label")
            yield TextArea("", id="cp-solution")

            yield Label("Tags — comma separated (optional)", classes="field-label")
            yield Input(placeholder="parsing, files, regex", id="cp-tags")

            with Horizontal(id="cp-actions"):
                yield Button("💾 Save Problem", id="btn-save-problem", classes="primary-btn")
                yield Button("Clear", id="btn-clear-form", classes="secondary-btn")
            yield Static("", id="cp-status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-problem":
            self._save()
        elif event.button.id == "btn-clear-form":
            self._clear()

    def _save(self) -> None:
        status = self.query_one("#cp-status", Static)
        try:
            examples = [
                {"input": self.query_one("#cp-ex1-in", Input).value,
                 "output": self.query_one("#cp-ex1-out", Input).value},
                {"input": self.query_one("#cp-ex2-in", Input).value,
                 "output": self.query_one("#cp-ex2-out", Input).value},
            ]
            problem = build_custom_problem(
                title=self.query_one("#cp-title", Input).value,
                description=self.query_one("#cp-description", TextArea).text,
                category=str(self.query_one("#cp-category", Select).value or "practical"),
                subcategory=self.query_one("#cp-subcategory", Input).value,
                difficulty=str(self.query_one("#cp-difficulty", Select).value or "medium"),
                examples=examples,
                hints=self.query_one("#cp-hints", TextArea).text.splitlines(),
                solution_code=self.query_one("#cp-solution", TextArea).text,
                tags=self.query_one("#cp-tags", Input).value.split(","),
            )
        except ValueError as e:
            status.update(f"[#f85149]✗ {e}[/#f85149]")
            return

        try:
            pid = self.app.problem_repo.create(problem.to_db())
            status.update(
                f"[green]✓ Saved “{problem.title}” (#{pid})[/green] — it can now appear "
                "in Free Practice and the review queue."
            )
            self._award_author_achievement()
            self._clear(keep_status=True)
        except Exception as e:
            status.update(f"[#f85149]✗ Could not save: {e}[/#f85149]")

    def _award_author_achievement(self) -> None:
        try:
            from codepractice.core.gamification import ACHIEVEMENTS_BY_KEY
            repo = self.app.gamification_repo
            if repo.custom_problem_count() >= 1 and repo.unlock("problem_author"):
                a = ACHIEVEMENTS_BY_KEY["problem_author"]
                self.notify(f"{a.icon} {a.name} — {a.description}",
                            title="Achievement unlocked!", timeout=8)
        except Exception:
            pass

    def _clear(self, keep_status: bool = False) -> None:
        for input_id in ("cp-title", "cp-subcategory", "cp-ex1-in", "cp-ex1-out",
                         "cp-ex2-in", "cp-ex2-out", "cp-tags"):
            self.query_one(f"#{input_id}", Input).value = ""
        for area_id in ("cp-description", "cp-hints", "cp-solution"):
            self.query_one(f"#{area_id}", TextArea).load_text("")
        if not keep_status:
            self.query_one("#cp-status", Static).update("")
