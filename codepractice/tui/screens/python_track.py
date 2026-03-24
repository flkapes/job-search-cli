"""Python fundamentals track — topic browser + drill mode."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, Select, Static

from codepractice.config import PYTHON_TOPICS


class TopicCard(Button):
    """Clickable topic card."""

    DEFAULT_CSS = """
    TopicCard {
        width: 1fr;
        height: 7;
        background: #161b22;
        border: solid #30363d;
        color: #c9d1d9;
        content-align: left middle;
        padding: 1 2;
        margin: 0 1 1 0;
    }

    TopicCard:hover {
        border: solid #58a6ff;
    }
    """


class PythonTrackContent(Widget):
    """Python fundamentals track browser."""

    DEFAULT_CSS = """
    PythonTrackContent {
        height: 1fr;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("[bold #58a6ff]🐍 Python Fundamentals Track[/bold #58a6ff]")
            yield Static(
                "[#8b949e]Master Python from core concepts to advanced patterns. "
                "Select a topic to start drilling.[/#8b949e]"
            )

            yield Label("", id="track-spacer")

            # Topic difficulty selector
            with Horizontal(id="difficulty-bar"):
                yield Label("Difficulty: ", id="diff-label")
                yield Select(
                    [(d, d) for d in ("easy", "medium", "hard")],
                    value="medium",
                    id="difficulty-select",
                )

            # Topic grid
            for topic in PYTHON_TOPICS:
                yield TopicCard(
                    f"{topic['icon']}  {topic['name']}\n[dim]{topic['description'][:70]}[/dim]",
                    id=f"topic-{topic['id']}",
                )

            yield Label("\n[bold]Your Progress[/bold]", classes="panel-title")
            yield DataTable(id="python-progress")

    def on_mount(self) -> None:
        self._load_progress()

    def _load_progress(self) -> None:
        table = self.query_one("#python-progress", DataTable)
        table.clear(columns=True)
        table.add_columns("Topic", "Attempted", "Solved", "Avg Score")
        try:
            scores = self.app.session_repo.get_category_scores()
            python_scores = [s for s in scores if s.get("category") == "python_fundamentals"]
            for s in python_scores:
                avg = f"{(s.get('avg_score', 0) or 0) * 100:.0f}%"
                table.add_row(
                    s.get("subcategory", "general"),
                    str(s.get("attempts", 0)),
                    str(s.get("solved", 0)),
                    avg,
                )
            if not python_scores:
                table.add_row("—", "No attempts yet", "—", "—")
        except Exception:
            table.add_row("—", "No data", "—", "—")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("topic-"):
            topic_id = btn_id.removeprefix("topic-")
            difficulty = self.query_one("#difficulty-select", Select).value
            self._start_drill(topic_id, str(difficulty))

    def _start_drill(self, topic_id: str, difficulty: str) -> None:
        """Switch to practice mode with this topic pre-selected."""
        # We use the app's content switching with a hint about what to practice
        from codepractice.tui.screens.practice import PracticeContent
        content = self.app.query_one("#content")
        content.remove_children()
        widget = PracticeContent()
        content.mount(widget)
        # After mounting, load a topic-specific problem
        widget.call_later(
            lambda: widget._load_next_problem(category="python_fundamentals", difficulty=difficulty)
        )
