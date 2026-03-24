"""Stats and streak display panels."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, Static

from codepractice.utils.text_utils import build_progress_bar


class StatCard(Static):
    """A single stat card showing value + label."""

    DEFAULT_CSS = """
    StatCard {
        height: 5;
        min-width: 18;
        background: #161b22;
        border: solid #30363d;
        padding: 1 2;
        content-align: center middle;
        margin: 0 1 0 0;
    }
    """

    def __init__(self, value: str, label: str, color: str = "#58a6ff", **kwargs):
        super().__init__(**kwargs)
        self._value = value
        self._label = label
        self._color = color

    def render(self) -> str:
        return f"[bold {self._color}]{self._value}[/bold {self._color}]\n[#8b949e]{self._label}[/#8b949e]"

    def update_stat(self, value: str, label: str | None = None) -> None:
        self._value = value
        if label:
            self._label = label
        self.refresh()


class StatsRow(Widget):
    """Horizontal row of stat cards."""

    DEFAULT_CSS = """
    StatsRow {
        height: auto;
        layout: horizontal;
        padding: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield StatCard("0", "Today", color="#3fb950", id="stat-today")
        yield StatCard("0", "Total Solved", color="#58a6ff", id="stat-total")
        yield StatCard("0%", "Avg Score", color="#bc8cff", id="stat-score")
        yield StatCard("0", "Day Streak", color="#d29922", id="stat-streak")

    def update_stats(self, today: int, total: int, avg_score: float, streak: int) -> None:
        self.query_one("#stat-today", StatCard).update_stat(str(today))
        self.query_one("#stat-total", StatCard).update_stat(str(total))
        self.query_one("#stat-score", StatCard).update_stat(f"{avg_score:.0f}%")
        self.query_one("#stat-streak", StatCard).update_stat(str(streak))


class PlanProgress(Widget):
    """Mini plan progress display."""

    DEFAULT_CSS = """
    PlanProgress {
        height: auto;
        padding: 1 2;
        background: #161b22;
        border: solid #30363d;
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("[bold]Active Plan[/bold]", id="plan-title")
        yield Static("No active plan", id="plan-info")
        yield Static("", id="plan-bar")

    def update_plan(self, title: str, current_day: int, total_days: int, theme: str = "") -> None:
        self.query_one("#plan-title", Label).update(f"[bold]📅 {title}[/bold]")
        bar = build_progress_bar(current_day, total_days, width=30)
        pct = int((current_day / total_days) * 100) if total_days > 0 else 0
        info = f"Day {current_day}/{total_days} — {pct}%"
        if theme:
            info += f"\n[#8b949e]Today: {theme}[/#8b949e]"
        self.query_one("#plan-info", Static).update(info)
        self.query_one("#plan-bar", Static).update(
            f"[#3fb950]{bar}[/#3fb950]"
        )

    def show_no_plan(self) -> None:
        self.query_one("#plan-title", Label).update("[bold]📅 Learning Plan[/bold]")
        self.query_one("#plan-info", Static).update(
            "[#8b949e]No active plan. Press [bold]L[/bold] to create one.[/#8b949e]"
        )
        self.query_one("#plan-bar", Static).update("")
