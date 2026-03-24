"""Progress screen — charts, streaks, category heatmaps, session history."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, Static

from codepractice.tui.widgets.stats_panel import StatsRow
from codepractice.utils.text_utils import build_progress_bar, score_to_color


class ReplayModal(ModalScreen):
    """Full-screen modal showing the user's submitted code and AI feedback side by side."""

    DEFAULT_CSS = """
    ReplayModal {
        align: center middle;
    }

    ReplayModal #replay-container {
        width: 90%;
        height: 85%;
        background: #161b22;
        border: solid #58a6ff;
        padding: 1;
    }

    ReplayModal #replay-header {
        height: 3;
        background: #1c2128;
        border-bottom: solid #30363d;
        padding: 0 2;
    }

    ReplayModal #replay-body {
        height: 1fr;
    }

    ReplayModal #replay-code {
        width: 1fr;
        border-right: solid #30363d;
        padding: 1;
    }

    ReplayModal #replay-feedback {
        width: 1fr;
        padding: 1;
    }

    ReplayModal #replay-close-bar {
        height: 3;
        background: #161b22;
        border-top: solid #30363d;
        padding: 0 2;
        dock: bottom;
    }
    """

    def __init__(self, attempt: dict, **kwargs):
        super().__init__(**kwargs)
        self._attempt = attempt

    def compose(self) -> ComposeResult:
        attempt = self._attempt
        score = attempt.get("ai_score", 0.0)
        score_pct = f"{score * 100:.0f}%"
        passed = "✓ Passed" if attempt.get("passed") else "✗ Failed"
        hints = attempt.get("hints_used", 0)
        elapsed = attempt.get("time_spent_sec", 0)
        title = attempt.get("problem_title", "Unknown Problem")

        with Vertical(id="replay-container"):
            with Horizontal(id="replay-header"):
                yield Label(
                    f"[bold]{title}[/bold]  "
                    f"Score: [cyan]{score_pct}[/cyan]  {passed}  "
                    f"Hints: {hints}  Time: {elapsed}s"
                )
            with Horizontal(id="replay-body"):
                with VerticalScroll(id="replay-code"):
                    yield Label("[bold #58a6ff]Your Code[/bold #58a6ff]")
                    yield Static(attempt.get("user_code", ""), id="code-display")
                with VerticalScroll(id="replay-feedback"):
                    yield Label("[bold #58a6ff]AI Feedback[/bold #58a6ff]")
                    yield Static(attempt.get("ai_feedback", ""), id="feedback-display")
            with Horizontal(id="replay-close-bar"):
                yield Button("Close [Escape]", id="btn-close-replay", classes="secondary-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-replay":
            self.dismiss()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()


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

    ProgressContent #drill-btn {
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

            yield Label("\n[bold]Weak Areas[/bold]", classes="panel-title")
            yield Static("", id="weak-areas-display", classes="chart-panel")
            yield Button("🎯 Fix My Gaps", id="btn-drill-weak", classes="primary-btn", disabled=True)

            yield Label("\n[bold]Recent Sessions[/bold]", classes="panel-title")
            yield DataTable(id="session-history")

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

            max_count = max(d.get("count", 0) for d in daily) or 1
            lines = []
            for d in daily[-14:]:
                day_str = d.get("day", "?")[-5:]
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
            from codepractice.core.difficulty import get_weak_areas, should_show_weak_area_drill
            scores = self.app.session_repo.get_category_scores()
            weak = get_weak_areas(scores)
            btn = self.query_one("#btn-drill-weak", Button)

            if weak:
                lines = ["[#d29922]Areas to focus on:[/#d29922]"]
                for area in weak:
                    lines.append(f"  • {area}")
                self.query_one("#weak-areas-display", Static).update("\n".join(lines))

                if should_show_weak_area_drill(scores):
                    btn.disabled = False
                    first_weak = weak[0]
                    btn.label = f"🎯 Fix My Gaps — Drilling: {first_weak}"
            else:
                self.query_one("#weak-areas-display", Static).update(
                    "[#8b949e]Not enough data yet to identify weak areas. Keep practicing![/#8b949e]"
                )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-drill-weak":
            self._start_weak_area_drill()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Open replay modal when a session row is clicked."""
        table = event.data_table
        if table.id == "session-history":
            # Not implemented: session → attempt listing (no row key stored)
            pass

    def _start_weak_area_drill(self) -> None:
        """Launch practice pre-filtered to the weakest category."""
        try:
            from codepractice.core.difficulty import get_weak_areas
            scores = self.app.session_repo.get_category_scores()
            weak = get_weak_areas(scores)
            if not weak:
                return

            # Parse "category/subcategory" string
            first = weak[0]
            parts = first.split("/", 1)
            cat = parts[0].strip() if parts else None
            sub = parts[1].strip() if len(parts) > 1 else None

            from codepractice.tui.screens.practice import PracticeContent
            content = self.app.query_one("#content")
            content.remove_children()
            widget = PracticeContent()
            content.mount(widget)
            # start_session with weak_area_drill type
            widget._init_session_type = "weak_area_drill"
            widget.call_later(widget._init_session)
            if cat:
                widget._drill_category = cat
                widget._drill_subcategory = sub
        except Exception:
            pass
