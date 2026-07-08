"""Company browser — searchable interview profiles with one-click targeted plans."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static

from codepractice.core.company_profiles import get_company, search_companies


class CompaniesContent(Widget):
    """Browse company interview profiles and generate a targeted learning plan."""

    DEFAULT_CSS = """
    CompaniesContent {
        height: 1fr;
        padding: 0 1;
    }

    CompaniesContent #company-search {
        margin: 1 0;
    }

    CompaniesContent #company-table {
        height: 12;
    }

    CompaniesContent #company-details {
        background: #161b22;
        border: solid #30363d;
        padding: 1 2;
        margin: 1 0;
    }

    CompaniesContent #prepare-bar {
        height: 3;
    }

    CompaniesContent #prepare-bar Select {
        width: 24;
        margin-right: 2;
    }
    """

    _row_company_ids: list[str] = []
    _selected_id: str | None = None

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("[bold #58a6ff]🏢 Company Prep Profiles[/bold #58a6ff]")
            yield Input(placeholder="Search companies (e.g. google, stripe)…", id="company-search")
            yield DataTable(id="company-table")
            yield Static("[#8b949e]Select a company to see its interview profile.[/#8b949e]", id="company-details")
            with Horizontal(id="prepare-bar"):
                yield Select(
                    [("7 days", "7"), ("14 days", "14"), ("30 days", "30")],
                    value="14",
                    id="prep-duration",
                    allow_blank=False,
                )
                yield Button("🎯 Prepare for this company", id="btn-prepare", classes="primary-btn", disabled=True)
            yield Static("", id="prepare-status")

    def on_mount(self) -> None:
        table = self.query_one("#company-table", DataTable)
        table.cursor_type = "row"
        self._load_table()

    def _load_table(self, query: str = "") -> None:
        table = self.query_one("#company-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Company", "Signature Patterns", "Round Length", "Hard %")
        self._row_company_ids = []
        for c in search_companies(query):
            patterns = ", ".join(p.replace("_", " ") for p in c.get("patterns", [])[:3])
            hard_pct = int(float(c.get("difficulty_distribution", {}).get("hard", 0)) * 100)
            self._row_company_ids.append(c["id"])
            table.add_row(
                c["name"],
                patterns,
                f"{c.get('typical_time_limit_min', 45)} min",
                f"{hard_pct}%",
            )
        if not self._row_company_ids:
            table.add_row("No matches", "—", "—", "—")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "company-search":
            self._load_table(event.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "company-table":
            return
        row = event.cursor_row
        if row < 0 or row >= len(self._row_company_ids):
            return
        self._selected_id = self._row_company_ids[row]
        self._show_details(self._selected_id)
        self.query_one("#btn-prepare", Button).disabled = False

    def _show_details(self, company_id: str) -> None:
        c = get_company(company_id)
        if not c:
            return
        dist = c.get("difficulty_distribution", {})
        lines = [
            f"[bold]{c['name']}[/bold]",
            "",
            "[#58a6ff]Common patterns:[/#58a6ff] "
            + ", ".join(p.replace("_", " ") for p in c.get("patterns", [])),
            "[#58a6ff]Focus areas:[/#58a6ff]",
        ]
        lines += [f"  • {f}" for f in c.get("focus_areas", [])]
        lines.append("[#58a6ff]Rounds:[/#58a6ff]")
        lines += [f"  • {r}" for r in c.get("rounds", [])]
        lines.append(
            f"[#58a6ff]Difficulty mix:[/#58a6ff] "
            f"easy {int(float(dist.get('easy', 0)) * 100)}% · "
            f"medium {int(float(dist.get('medium', 0)) * 100)}% · "
            f"hard {int(float(dist.get('hard', 0)) * 100)}%"
        )
        if c.get("notes"):
            lines.append(f"\n[#d29922]💡 {c['notes']}[/#d29922]")
        self.query_one("#company-details", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-prepare":
            self._prepare()

    def _prepare(self) -> None:
        status = self.query_one("#prepare-status", Static)
        if not self._selected_id:
            return
        company = get_company(self._selected_id)
        if not company:
            return
        duration = int(self.query_one("#prep-duration", Select).value or "14")
        status.update(f"[#58a6ff]Building your {company['name']} plan…[/#58a6ff]")

        try:
            from codepractice.core.company_profiles import build_company_plan, company_goal_text

            plan = None
            goal = company_goal_text(company, duration)
            try:
                if self.app.llm.health_check():
                    from codepractice.core.models import UserProfile
                    from codepractice.llm.services.plan_manager import LearningPlanManager
                    profile_data = self.app.profile_repo.get()
                    profile = UserProfile.from_db(profile_data) if profile_data else None
                    plan = LearningPlanManager(self.app.llm).create_plan(goal, duration, profile)
            except Exception:
                plan = None
            if plan is None:
                plan = build_company_plan(company, duration)

            plan_id = self.app.plan_repo.create({
                "title": plan.title,
                "natural_language_goal": goal,
                "duration_days": duration,
                "plan": plan.model_dump(),
            })
            for day in plan.daily_schedule:
                self.app.plan_repo.add_day(plan_id, {
                    "day_number": day.day_number,
                    "theme": day.theme,
                    "objectives": day.objectives,
                    "estimated_minutes": day.estimated_minutes,
                })
            status.update(
                f"[green]✓ Plan created: {plan.title}[/green]\n"
                f"[#8b949e]{len(plan.daily_schedule)} days scheduled — "
                f"open the Learning Plan screen (L) to start.[/#8b949e]"
            )
        except Exception as e:
            status.update(f"[#f85149]Could not create plan: {e}[/#f85149]")
