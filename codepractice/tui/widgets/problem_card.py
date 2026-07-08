"""Rich problem statement display panel."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Label, Markdown, Static, TextArea

from codepractice.core.models import Problem
from codepractice.utils.text_utils import difficulty_badge


class ProblemCard(Widget):
    """Displays a coding problem with title, description, examples, and hints."""

    DEFAULT_CSS = """
    ProblemCard {
        height: auto;
        min-height: 8;
    }

    ProblemCard #problem-header {
        height: auto;
        background: #1c2128;
        padding: 1 2;
        border-bottom: solid #30363d;
    }

    ProblemCard .problem-title-text {
        text-style: bold;
        color: #ffffff;
    }

    ProblemCard .problem-meta {
        color: #8b949e;
        margin-top: 0;
    }

    ProblemCard #problem-body {
        padding: 1 2;
        height: auto;
    }

    ProblemCard .example-block {
        background: #0d1117;
        padding: 1 2;
        margin: 1 0;
        border: solid #30363d;
    }

    ProblemCard .example-label {
        color: #58a6ff;
        text-style: bold;
    }

    ProblemCard .hint-text {
        color: #d29922;
        margin: 0 0 0 2;
    }

    ProblemCard #title-row {
        height: auto;
    }

    ProblemCard #btn-bookmark {
        dock: right;
        min-width: 5;
        background: transparent;
        border: none;
        color: #d29922;
    }
    """

    _problem: Problem | None = None
    _hints_shown: int = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="problem-header"):
            with Horizontal(id="title-row"):
                yield Label("No problem loaded", classes="problem-title-text", id="p-title")
                yield Button("☆", id="btn-bookmark")
            yield Label("", classes="problem-meta", id="p-meta")
        with VerticalScroll(id="problem-body"):
            yield Markdown("", id="p-description")
            yield Static("", id="p-examples")
            yield Static("", id="p-hints-area")
            yield Label("[dim]📝 My Notes (auto-saved)[/dim]", id="notes-label")
            yield TextArea("", id="p-notes")

    def load_problem(self, problem: Problem) -> None:
        self._problem = problem
        self._hints_shown = 0

        # Title and metadata
        self.query_one("#p-title", Label).update(problem.title)
        badge = difficulty_badge(problem.difficulty.value if hasattr(problem.difficulty, 'value') else problem.difficulty)
        tags = " ".join(f"[dim]#{t}[/dim]" for t in problem.tags[:5])
        category_display = problem.category.replace("_", " ").title()
        self.query_one("#p-meta", Label).update(
            f"{badge}  {category_display}  {tags}"
        )

        # Description
        self.query_one("#p-description", Markdown).update(problem.description)

        # Examples
        examples_text = ""
        for i, ex in enumerate(problem.examples, 1):
            examples_text += f"[#58a6ff bold]Example {i}:[/#58a6ff bold]\n"
            if ex.input:
                examples_text += f"  Input:  [bold]{ex.input}[/bold]\n"
            if ex.output:
                examples_text += f"  Output: [bold]{ex.output}[/bold]\n"
            if ex.explanation:
                examples_text += f"  [dim]{ex.explanation}[/dim]\n"
            examples_text += "\n"

        if problem.constraints:
            examples_text += f"[#8b949e]Constraints: {problem.constraints}[/#8b949e]\n"

        self.query_one("#p-examples", Static).update(examples_text)
        self.query_one("#p-hints-area", Static).update("")

        # Load saved note for this problem
        try:
            if problem.id:
                note = self.app.problem_repo.get_note(problem.id)
                self.query_one("#p-notes", TextArea).load_text(note)
        except Exception:
            pass

        self._refresh_bookmark_button()

    def _refresh_bookmark_button(self) -> None:
        try:
            btn = self.query_one("#btn-bookmark", Button)
            if self._problem and self._problem.id:
                bookmarked = self.app.problem_repo.is_bookmarked(self._problem.id)
                btn.label = "★" if bookmarked else "☆"
                btn.disabled = False
            else:
                btn.label = "☆"
                btn.disabled = True
        except Exception:
            pass

    def toggle_bookmark(self) -> bool | None:
        """Flip the bookmark state. Returns the new state, or None if unavailable."""
        if not self._problem or not self._problem.id:
            return None
        try:
            new_state = not self.app.problem_repo.is_bookmarked(self._problem.id)
            self.app.problem_repo.set_bookmark(self._problem.id, new_state)
            self._refresh_bookmark_button()
            return new_state
        except Exception:
            return None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-bookmark":
            event.stop()
            state = self.toggle_bookmark()
            if state is not None:
                self.app.notify(
                    "Bookmarked — find it in My Library" if state else "Bookmark removed",
                    timeout=3,
                )

    def show_next_hint(self) -> str | None:
        """Reveal the next hint. Returns the hint text or None if all shown."""
        if not self._problem or not self._problem.hints:
            return None
        if self._hints_shown >= len(self._problem.hints):
            return None

        hint = self._problem.hints[self._hints_shown]
        self._hints_shown += 1

        hints_display = ""
        for i in range(self._hints_shown):
            hints_display += f"[#d29922]💡 Hint {i + 1}:[/#d29922] {self._problem.hints[i]}\n"

        remaining = len(self._problem.hints) - self._hints_shown
        if remaining > 0:
            hints_display += f"[dim]({remaining} more hint{'s' if remaining > 1 else ''} available — press H)[/dim]"

        self.query_one("#p-hints-area", Static).update(hints_display)
        return hint

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Auto-save notes on every change."""
        if event.text_area.id == "p-notes" and self._problem and self._problem.id:
            try:
                self.app.problem_repo.save_note(self._problem.id, event.text_area.text)
            except Exception:
                pass

    def clear_problem(self) -> None:
        self._problem = None
        self._hints_shown = 0
        self.query_one("#p-title", Label).update("No problem loaded")
        self.query_one("#p-meta", Label).update("")
        self.query_one("#p-description", Markdown).update("")
        self.query_one("#p-examples", Static).update("")
        self.query_one("#p-hints-area", Static).update("")
        try:
            self.query_one("#p-notes", TextArea).load_text("")
        except Exception:
            pass
        self._refresh_bookmark_button()
