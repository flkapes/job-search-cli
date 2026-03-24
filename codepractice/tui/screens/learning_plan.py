"""Learning plan — NL goal input, AI plan generation, day-by-day view."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static

from codepractice.tui.widgets.streaming_output import StreamingOutput
from codepractice.utils.text_utils import build_progress_bar


class LearningPlanContent(Widget):
    """Adaptive learning plan management."""

    DEFAULT_CSS = """
    LearningPlanContent {
        height: 1fr;
        padding: 0 1;
    }

    LearningPlanContent #plan-create-section {
        background: #161b22;
        border: solid #30363d;
        padding: 1 2;
        margin: 1 0;
    }

    LearningPlanContent #plan-view {
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("[bold #58a6ff]📅 Adaptive Learning Plan[/bold #58a6ff]")
            yield Static(
                "[#8b949e]Describe your goal in natural language. "
                "The AI creates a structured day-by-day plan that adapts "
                "based on your performance over time.[/#8b949e]\n"
            )

            # Create new plan section
            with Vertical(id="plan-create-section"):
                yield Label("[bold]Create New Plan[/bold]")
                yield Input(
                    placeholder='e.g., "Prepare me for a backend Python interview in 14 days"',
                    id="plan-goal-input",
                )
                with Horizontal():
                    yield Label("Duration: ")
                    yield Select(
                        [("7 days", "7"), ("14 days", "14"), ("30 days", "30"), ("60 days", "60")],
                        value="14",
                        id="plan-duration",
                    )
                    yield Button("🚀 Generate Plan", id="btn-create-plan", classes="primary-btn")

            yield StreamingOutput(id="plan-gen-output")

            # Active plan view
            yield Vertical(id="plan-view")
            yield Label("", id="plan-header-label")
            yield Static("", id="plan-progress-bar")
            yield Label("\n[bold]Daily Schedule[/bold]", classes="panel-title")
            yield DataTable(id="plan-schedule")

            with Horizontal():
                yield Button("▶ Start Today's Practice", id="btn-start-day", classes="primary-btn")
                yield Button("🔄 Evolve Plan", id="btn-evolve", classes="secondary-btn")
                yield Button("⏸ Pause Plan", id="btn-pause", classes="secondary-btn")

    def on_mount(self) -> None:
        self._load_active_plan()

    def _load_active_plan(self) -> None:
        try:
            plan = self.app.plan_repo.get_active()
            if plan:
                self._display_plan(plan)
            else:
                self.query_one("#plan-header-label", Label).update(
                    "[#8b949e]No active plan. Create one above![/#8b949e]"
                )
                table = self.query_one("#plan-schedule", DataTable)
                table.clear(columns=True)
        except Exception:
            pass

    def _display_plan(self, plan: dict) -> None:
        self.query_one("#plan-header-label", Label).update(
            f"[bold]{plan['title']}[/bold]"
        )
        current = plan.get("current_day", 1)
        total = plan.get("duration_days", 30)
        bar = build_progress_bar(current, total, width=40)
        pct = int((current / total) * 100) if total > 0 else 0
        self.query_one("#plan-progress-bar", Static).update(
            f"Day {current}/{total} ({pct}%) [#3fb950]{bar}[/#3fb950]"
        )

        # Load days
        days = self.app.plan_repo.get_days(plan["id"])
        table = self.query_one("#plan-schedule", DataTable)
        table.clear(columns=True)
        table.add_columns("Day", "Theme", "Est.", "Status")
        for d in days[:30]:
            day_num = d.get("day_number", 0)
            status = "[green]✓[/green]" if d.get("completed") else (
                "[#58a6ff]▶ TODAY[/#58a6ff]" if day_num == current else "[dim]—[/dim]"
            )
            table.add_row(
                str(day_num),
                d.get("theme", "—"),
                f"{d.get('estimated_minutes', 45)}m",
                status,
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-create-plan":
            self._create_plan()
        elif event.button.id == "btn-start-day":
            self._start_today()
        elif event.button.id == "btn-evolve":
            self._evolve_plan()
        elif event.button.id == "btn-pause":
            self._pause_plan()

    def _create_plan(self) -> None:
        goal = self.query_one("#plan-goal-input", Input).value
        if not goal.strip():
            self.query_one("#plan-gen-output", StreamingOutput).show_error(
                "Please describe your learning goal."
            )
            return

        duration = int(self.query_one("#plan-duration", Select).value or "14")
        stream = self.query_one("#plan-gen-output", StreamingOutput)
        stream.clear()
        stream.show_info(f"Generating your {duration}-day plan...")

        try:
            profile = None
            profile_data = self.app.profile_repo.get()
            if profile_data:
                from codepractice.core.models import UserProfile
                profile = UserProfile.from_db(profile_data)

            from codepractice.llm.services.plan_manager import LearningPlanManager
            mgr = LearningPlanManager(self.app.llm)
            plan = mgr.create_plan(goal, duration, profile)

            if plan:
                # Save to DB
                plan_id = self.app.plan_repo.create({
                    "title": plan.title,
                    "natural_language_goal": goal,
                    "duration_days": duration,
                    "plan": plan.model_dump(),
                })
                # Save day entries
                for day in plan.daily_schedule:
                    self.app.plan_repo.add_day(plan_id, {
                        "day_number": day.day_number,
                        "theme": day.theme,
                        "objectives": day.objectives,
                        "estimated_minutes": day.estimated_minutes,
                    })

                stream.write_line(f"\n[green]✓ Plan created: {plan.title}[/green]")
                stream.write_line(f"[#8b949e]{len(plan.daily_schedule)} days scheduled[/#8b949e]")

                self._load_active_plan()
            else:
                stream.show_error("Could not generate plan. Check LLM connection.")
        except Exception as e:
            stream.show_error(f"Error: {e}")

    def _start_today(self) -> None:
        """Jump to practice mode for today's plan tasks."""
        self.app._switch_content("practice")

    def _evolve_plan(self) -> None:
        stream = self.query_one("#plan-gen-output", StreamingOutput)
        stream.clear()
        stream.show_info("Analyzing your progress and updating the plan...")

        try:
            plan = self.app.plan_repo.get_active()
            if not plan:
                stream.show_error("No active plan to evolve.")
                return

            from codepractice.core.difficulty import get_weak_areas
            from codepractice.core.models import LearningPlan
            from codepractice.llm.services.plan_manager import LearningPlanManager

            scores = self.app.session_repo.get_category_scores()
            weak = get_weak_areas(scores)
            stats = self.app.session_repo.get_stats()
            perf = f"Avg score: {stats['avg_score']}%, Solved: {stats['total_solved']}, Active days: {stats['active_days_30']}"

            # Reconstruct the plan model
            lp = LearningPlan(
                id=plan["id"],
                title=plan["title"],
                natural_language_goal=plan.get("natural_language_goal", ""),
                duration_days=plan.get("duration_days", 30),
                current_day=plan.get("current_day", 1),
            )

            mgr = LearningPlanManager(self.app.llm)
            updated = mgr.evolve_plan(lp, perf, weak)

            if updated:
                self.app.plan_repo.update_plan_json(plan["id"], updated.model_dump())
                stream.write_line("[green]✓ Plan updated based on your progress![/green]")
                self._load_active_plan()
        except Exception as e:
            stream.show_error(f"Error: {e}")

    def _pause_plan(self) -> None:
        try:
            plan = self.app.plan_repo.get_active()
            if plan:
                self.app.plan_repo.update_status(plan["id"], "paused")
                self._load_active_plan()
        except Exception:
            pass
