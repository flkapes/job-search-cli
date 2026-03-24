"""Progress screen — charts, streaks, category heatmaps, session history."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import DataTable, Label, Static

from codepractice.tui.widgets.stats_panel import StatsRow
from codepractice.utils.text_utils import build_progress_bar, score_to_color


class ProgressContent(Widget):
    """Progress tracking and analytics."""

    DEFAULT_CSS = """
    ProgressContent {
        height: 1fr;
        padding: 0 1;
    }

    ProgressContent .chart-panel {
        background: #161b22;
        border: solid #30363d;
        padding: 1 2;
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("[bold #58a6ff]📊 Your Progress[/bold #58a6ff]\n")
            yield StatsRow(id="progress-stats")

            yield Label("\n[bold]30-Day Activity[/bold]", classes="panel-title")
            yield Static("", id="activity-chart", classes="chart-panel")

            yield Label("\n[bold]Category Mastery[/bold]", classes="panel-title")
            yield DataTable(id="category-mastery")

            yield Label("\n[bold]Recent Sessions[/bold]", classes="panel-title")
            yield DataTable(id="session-history")

            yield Label("\n[bold]Weak Areas[/bold]", classes="panel-title")
            yield Static("", id="weak-areas-display", classes="chart-panel")

    def on_mount(self) -> None:
        self._load_all()

    def _load_all(self) -> None:
        self._load_stats()
        self._load_activity()
        self._load_mastery()
        self._load_sessions()
        self._load_weak_areas()

    def _load_stats(self) -> None:
        try:
            stats = self.app.session_repo.get_stats()
            row = self.query_one("#progress-stats", StatsRow)
            row.update_stats(
                today=stats.get("today_solved", 0),
                total=stats.get("total_solved", 0),
                avg_score=stats.get("avg_score", 0),
                streak=stats.get("active_days_30", 0),
            )
        except Exception:
            pass

    def _load_activity(self) -> None:
        try:
            daily = self.app.session_repo.get_daily_activity(30)
            if not daily:
                self.query_one("#activity-chart", Static).update(
                    "[#8b949e]No activity in the last 30 days. Start practicing![/#8b949e]"
                )
                return

            # Build a simple text-based bar chart
            max_count = max(d.get("count", 0) for d in daily) or 1
            lines = []
            for d in daily[-14:]:  # Last 14 days
                day_str = d.get("day", "?")[-5:]  # MM-DD
                count = d.get("count", 0)
                bar_width = int((count / max_count) * 30) if max_count > 0 else 0
                bar = "█" * bar_width
                avg = d.get("avg_score", 0) or 0
                color = score_to_color(avg)
                lines.append(f"  {day_str} [{color}]{bar}[/{color}] {count}")

            self.query_one("#activity-chart", Static).update("\n".join(lines))
        except Exception:
            pass

    def _load_mastery(self) -> None:
        table = self.query_one("#category-mastery", DataTable)
        table.clear(columns=True)
        table.add_columns("Category", "Topic", "Attempts", "Solved", "Avg Score", "Mastery")
        try:
            scores = self.app.session_repo.get_category_scores()
            for s in scores:
                avg = (s.get("avg_score", 0) or 0) * 100
                bar = build_progress_bar(int(avg), 100, width=10)
                color = score_to_color(avg / 100)
                table.add_row(
                    s.get("category", "—"),
                    s.get("subcategory", "—"),
                    str(s.get("attempts", 0)),
                    str(s.get("solved", 0)),
                    f"{avg:.0f}%",
                    f"[{color}]{bar}[/{color}]",
                )
            if not scores:
                table.add_row("—", "No data yet", "—", "—", "—", "—")
        except Exception:
            table.add_row("—", "Error loading data", "—", "—", "—", "—")

    def _load_sessions(self) -> None:
        table = self.query_one("#session-history", DataTable)
        table.clear(columns=True)
        table.add_columns("Date", "Type", "Problems", "Solved", "Duration")
        try:
            sessions = self.app.session_repo.get_recent_sessions(limit=10)
            for s in sessions:
                started = str(s.get("started_at", ""))[:16]
                table.add_row(
                    started,
                    s.get("session_type", "free"),
                    str(s.get("total_problems", 0)),
                    str(s.get("solved_count", 0)),
                    "—",
                )
            if not sessions:
                table.add_row("—", "No sessions yet", "—", "—", "—")
        except Exception:
            pass

    def _load_weak_areas(self) -> None:
        try:
            from codepractice.core.difficulty import get_weak_areas
            scores = self.app.session_repo.get_category_scores()
            weak = get_weak_areas(scores)
            if weak:
                lines = ["[#d29922]Areas to focus on:[/#d29922]"]
                for area in weak:
                    lines.append(f"  • {area}")
                self.query_one("#weak-areas-display", Static).update("\n".join(lines))
            else:
                self.query_one("#weak-areas-display", Static).update(
                    "[#8b949e]Not enough data yet to identify weak areas. Keep practicing![/#8b949e]"
                )
        except Exception:
            pass
