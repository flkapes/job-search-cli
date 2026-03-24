"""DSA pattern browser + structured drills."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, Select, Static

from codepractice.config import DSA_PATTERNS


class PatternCard(Button):
    """Clickable DSA pattern card."""

    DEFAULT_CSS = """
    PatternCard {
        width: 1fr;
        height: 5;
        background: #161b22;
        border: solid #30363d;
        color: #c9d1d9;
        content-align: left middle;
        padding: 1 2;
        margin: 0 1 1 0;
    }

    PatternCard:hover {
        border: solid #58a6ff;
    }
    """


class DSATrainingContent(Widget):
    """DSA pattern training browser."""

    DEFAULT_CSS = """
    DSATrainingContent {
        height: 1fr;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("[bold #58a6ff]🧩 DSA Pattern Training[/bold #58a6ff]")
            yield Static(
                "[#8b949e]Master the core patterns that appear in coding interviews. "
                "Each pattern has a focused drill set.[/#8b949e]\n"
            )

            with Horizontal(id="dsa-diff-bar"):
                yield Label("Difficulty: ")
                yield Select(
                    [(d, d) for d in ("easy", "medium", "hard")],
                    value="medium",
                    id="dsa-difficulty",
                )

            # Pattern grid (2 columns)
            for i in range(0, len(DSA_PATTERNS), 2):
                with Horizontal():
                    p = DSA_PATTERNS[i]
                    yield PatternCard(
                        f"{p['icon']}  {p['name']}\n[dim]{p['description'][:60]}[/dim]",
                        id=f"dsa-{p['id']}",
                    )
                    if i + 1 < len(DSA_PATTERNS):
                        p2 = DSA_PATTERNS[i + 1]
                        yield PatternCard(
                            f"{p2['icon']}  {p2['name']}\n[dim]{p2['description'][:60]}[/dim]",
                            id=f"dsa-{p2['id']}",
                        )

            yield Label("\n[bold]Pattern Mastery[/bold]", classes="panel-title")
            yield DataTable(id="dsa-progress")

    def on_mount(self) -> None:
        self._load_progress()

    def _load_progress(self) -> None:
        table = self.query_one("#dsa-progress", DataTable)
        table.clear(columns=True)
        table.add_columns("Pattern", "Attempted", "Solved", "Avg Score")
        try:
            scores = self.app.session_repo.get_category_scores()
            dsa_scores = [s for s in scores if s.get("category") == "dsa"]
            for s in dsa_scores:
                avg = f"{(s.get('avg_score', 0) or 0) * 100:.0f}%"
                table.add_row(
                    s.get("subcategory", "general"),
                    str(s.get("attempts", 0)),
                    str(s.get("solved", 0)),
                    avg,
                )
            if not dsa_scores:
                table.add_row("—", "No attempts yet", "—", "—")
        except Exception:
            table.add_row("—", "No data", "—", "—")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("dsa-"):
            pattern_id = btn_id.removeprefix("dsa-")
            difficulty = self.query_one("#dsa-difficulty", Select).value
            self._start_pattern_drill(pattern_id, str(difficulty))

    def _start_pattern_drill(self, pattern_id: str, difficulty: str) -> None:
        from codepractice.tui.screens.practice import PracticeContent
        content = self.app.query_one("#content")
        content.remove_children()
        widget = PracticeContent()
        content.mount(widget)
        widget.call_later(
            lambda: widget._load_next_problem(category="dsa", difficulty=difficulty)
        )
