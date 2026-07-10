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

    _session_row_ids: list[int | None] = []

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("[bold #58a6ff]📊 Your Progress[/bold #58a6ff]\n")
            yield StatsRow(id="progress-stats")

            yield Label("\n[bold]Level & XP[/bold]", classes="panel-title")
            yield Static("", id="xp-panel", classes="chart-panel")

            yield Label("\n[bold]Achievements[/bold]", classes="panel-title")
            yield Static("", id="achievements-gallery", classes="chart-panel")

            yield Label("\n[bold]30-Day Activity[/bold]", classes="panel-title")
            yield Static("", id="activity-chart", classes="chart-panel")

            yield Label("\n[bold]Category Mastery[/bold]", classes="panel-title")
            yield DataTable(id="category-mastery")

            yield Label("\n[bold]Weak Areas[/bold]", classes="panel-title")
            yield Static("", id="weak-areas-display", classes="chart-panel")
            yield Button("🎯 Fix My Gaps", id="btn-drill-weak", classes="primary-btn", disabled=True)

            yield Label("\n[bold]Goal History / Drift[/bold]", classes="panel-title")
            yield Static("", id="goal-history-panel", classes="chart-panel")

            yield Label("\n[bold]Recent Sessions[/bold]", classes="panel-title")
            yield DataTable(id="session-history")

    def on_mount(self) -> None:
        self._load_all()

    def _load_all(self) -> None:
        self._load_stats()
        self._load_xp()
        self._load_achievements()
        self._load_activity()
        self._load_mastery()
        self._load_sessions()
        self._load_weak_areas()
        self._load_goal_history()

    def _load_xp(self) -> None:
        try:
            from codepractice.core.gamification import level_for_xp
            total = self.app.gamification_repo.total_xp()
            info = level_for_xp(total)
            bar = build_progress_bar(int(info.progress_to_next * 100), 100, width=24)
            if info.next_threshold is not None:
                next_line = f"{info.xp}/{info.next_threshold} XP to next level"
            else:
                next_line = "Max level reached!"
            lines = [
                f"[bold #bc8cff]Level {info.level} — {info.title}[/bold #bc8cff]",
                f"  [#bc8cff]{bar}[/#bc8cff]  {next_line}",
            ]

            history = self.app.gamification_repo.xp_by_day(14)
            if history:
                max_xp = max(d.get("xp", 0) for d in history) or 1
                lines.append("\n[bold]XP — last 14 days[/bold]")
                for d in history:
                    day_str = str(d.get("day", "?"))[-5:]
                    xp = d.get("xp", 0)
                    bar_width = int((xp / max_xp) * 30) if max_xp else 0
                    lines.append(f"  {day_str} [#bc8cff]{'█' * bar_width}[/#bc8cff] {xp}")
            self.query_one("#xp-panel", Static).update("\n".join(lines))
        except Exception:
            pass

    def _load_achievements(self) -> None:
        try:
            from codepractice.core.gamification import ACHIEVEMENTS
            unlocked = self.app.gamification_repo.unlocked_keys()
            lines = []
            for a in ACHIEVEMENTS:
                if a.key in unlocked:
                    lines.append(f"  {a.icon} [bold #3fb950]{a.name}[/bold #3fb950] — {a.description}")
                else:
                    lines.append(f"  [dim]🔒 {a.name} — {a.description}[/dim]")
            header = f"[#8b949e]{len(unlocked)}/{len(ACHIEVEMENTS)} unlocked[/#8b949e]\n"
            self.query_one("#achievements-gallery", Static).update(header + "\n".join(lines))
        except Exception:
            pass

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
        self._session_row_ids = []
        try:
            sessions = self.app.session_repo.get_recent_sessions(limit=10)
            for s in sessions:
                started = str(s.get("started_at", ""))[:16]
                self._session_row_ids.append(s.get("id"))
                table.add_row(
                    started,
                    s.get("session_type", "free"),
                    str(s.get("total_problems", 0)),
                    str(s.get("solved_count", 0)),
                    "—",
                )
            if not sessions:
                self._session_row_ids.append(None)
                table.add_row("—", "No sessions yet", "—", "—", "—")
        except Exception:
            self._session_row_ids = []

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
            row_index = event.cursor_row
            if row_index < 0 or row_index >= len(self._session_row_ids):
                return
            session_id = self._session_row_ids[row_index]
            if not session_id:
                return

            try:
                attempt = self.app.session_repo.get_latest_attempt_for_session(session_id)
                if attempt:
                    self.app.push_screen(ReplayModal(attempt))
                else:
                    self.notify("No attempts found for this session yet.", severity="information")
            except Exception:
                self.notify("Could not load session replay.", severity="error")

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
            content.mount(PracticeContent(
                session_type="weak_area_drill",
                drill_category=cat,
                drill_subcategory=sub,
            ))
        except Exception:
            pass


    def _load_goal_history(self) -> None:
        try:
            entries = self.app.goal_history_repo.list_recent(limit=6)
            if not entries:
                self.query_one("#goal-history-panel", Static).update("[#8b949e]No goal updates yet.[/#8b949e]")
                return
            lines = []
            for e in entries:
                created = str(e.get("created_at", ""))[:16]
                goal = e.get("goal_text", "")
                lines.append(f"  {created} • {goal[:80]}")
            self.query_one("#goal-history-panel", Static).update("\n".join(lines))
        except Exception:
            pass
