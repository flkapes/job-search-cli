"""Dashboard — home screen with stats, quick actions, and plan overview."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, Static

from codepractice.tui.widgets.stats_panel import PlanProgress, StatsRow
from codepractice.tui.widgets.welcome_banner import WelcomeBanner


class QuickAction(Button):
    """Styled quick-action card button."""

    DEFAULT_CSS = """
    QuickAction {
        width: 1fr;
        height: 5;
        background: #161b22;
        border: solid #30363d;
        color: #c9d1d9;
        content-align: center middle;
        margin: 0 1 1 0;
        text-style: bold;
    }

    QuickAction:hover {
        border: solid #58a6ff;
        color: #58a6ff;
    }
    """


class DashboardContent(Widget):
    """Main dashboard content widget."""

    DEFAULT_CSS = """
    DashboardContent {
        height: 1fr;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield WelcomeBanner()
            yield StatsRow(id="dashboard-stats")

            yield Label("[bold]Quick Start[/bold]", classes="panel-title")
            with Horizontal(classes="action-grid"):
                yield QuickAction("⚡ Free Practice", id="qa-practice")
                yield QuickAction("🐍 Python Track", id="qa-python")
                yield QuickAction("🧩 DSA Patterns", id="qa-dsa")
            with Horizontal(classes="action-grid"):
                yield QuickAction("📄 Resume Drill", id="qa-resume")
                yield QuickAction("💼 Job Prep", id="qa-jd")
                yield QuickAction("💬 AI Coach", id="qa-chat")

            yield PlanProgress(id="dashboard-plan")

            yield Label("[bold]Recent Activity[/bold]", classes="panel-title")
            yield DataTable(id="recent-activity")

    def on_mount(self) -> None:
        self._load_stats()
        self._load_plan()
        self._load_recent()

    def _load_stats(self) -> None:
        app = self.app
        try:
            stats = app.session_repo.get_stats()
            row = self.query_one("#dashboard-stats", StatsRow)
            row.update_stats(
                today=stats.get("today_solved", 0),
                total=stats.get("total_solved", 0),
                avg_score=stats.get("avg_score", 0),
                streak=stats.get("active_days_30", 0),
            )
        except Exception:
            pass

    def _load_plan(self) -> None:
        app = self.app
        try:
            plan = app.plan_repo.get_active()
            progress = self.query_one("#dashboard-plan", PlanProgress)
            if plan:
                days = app.plan_repo.get_days(plan["id"])
                today_day = next(
                    (d for d in days if d["day_number"] == plan.get("current_day", 1)),
                    None,
                )
                progress.update_plan(
                    title=plan["title"],
                    current_day=plan.get("current_day", 1),
                    total_days=plan.get("duration_days", 30),
                    theme=today_day.get("theme", "") if today_day else "",
                )
            else:
                progress.show_no_plan()
        except Exception:
            pass

    def _load_recent(self) -> None:
        app = self.app
        table = self.query_one("#recent-activity", DataTable)
        table.clear(columns=True)
        table.add_columns("Date", "Type", "Problems", "Score")
        try:
            sessions = app.session_repo.get_recent_sessions(limit=5)
            for s in sessions:
                score = "—"
                table.add_row(
                    str(s.get("started_at", ""))[:10],
                    s.get("session_type", "free"),
                    str(s.get("solved_count", 0)) + "/" + str(s.get("total_problems", 0)),
                    score,
                )
            if not sessions:
                table.add_row("—", "No sessions yet", "—", "—")
        except Exception:
            table.add_row("—", "No data", "—", "—")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        screen_map = {
            "qa-practice": "practice",
            "qa-python": "python_track",
            "qa-dsa": "dsa_training",
            "qa-resume": "resume_drill",
            "qa-jd": "job_desc",
            "qa-chat": "chat",
        }
        target = screen_map.get(event.button.id or "")
        if target:
            self.app._switch_content(target)
