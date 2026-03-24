"""Job description screen — paste JD, AI generates practical problems."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static, TextArea

from codepractice.tui.widgets.streaming_output import StreamingOutput


class JobDescContent(Widget):
    """Paste a job description → AI generates role-specific practice."""

    DEFAULT_CSS = """
    JobDescContent {
        height: 1fr;
        padding: 0 1;
    }
    """

    _generated_problems: list = []

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("[bold #58a6ff]💼 Job Description Prep[/bold #58a6ff]")
            yield Static(
                "[#8b949e]Paste a job description below. The AI will analyze the required skills "
                "and generate practical coding problems that prepare you for this specific role — "
                "focused on real-world tasks, not just abstract algorithms.[/#8b949e]\n"
            )

            with Horizontal():
                yield Input(placeholder="Company name (optional)", id="jd-company")
                yield Input(placeholder="Role title (optional)", id="jd-role")

            yield Label("[bold]Job Description[/bold]")
            yield TextArea("", id="jd-input")

            with Horizontal():
                yield Button("🎯 Generate Problems", id="btn-gen-jd", classes="primary-btn")
                yield Label("  Problems: ", id="jd-count-label")
                yield Select(
                    [("3", "3"), ("5", "5"), ("8", "8")],
                    value="5",
                    id="jd-count",
                )

            yield Label("\n[bold]Analysis & Problems[/bold]", classes="panel-title")
            yield StreamingOutput(id="jd-output")
            yield Static("", id="jd-problem-list")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-gen-jd":
            self._generate()

    def _generate(self) -> None:
        jd_text = self.query_one("#jd-input", TextArea).text
        if not jd_text.strip():
            self.query_one("#jd-output", StreamingOutput).show_error(
                "Please paste a job description first."
            )
            return

        company = self.query_one("#jd-company", Input).value
        role = self.query_one("#jd-role", Input).value
        count = int(self.query_one("#jd-count", Select).value or "5")

        stream = self.query_one("#jd-output", StreamingOutput)
        stream.clear()
        stream.show_info(
            f"Analyzing job description{' for ' + company if company else ''}..."
        )

        # Save JD
        try:
            from codepractice.db.database import get_db
            from codepractice.db.repositories.base import BaseRepository
            db = get_db()
            with db.get_connection() as conn:
                conn.execute(
                    "INSERT INTO job_descriptions (company_name, role_title, jd_text) VALUES (?,?,?)",
                    (company, role, jd_text),
                )
        except Exception:
            pass

        # Generate
        try:
            profile = None
            profile_data = self.app.profile_repo.get()
            if profile_data:
                from codepractice.core.models import UserProfile
                profile = UserProfile.from_db(profile_data)

            from codepractice.llm.services.problem_generator import ProblemGeneratorService
            gen = ProblemGeneratorService(self.app.llm)
            problems = gen.generate_from_jd(jd_text, count, profile)

            if problems:
                stream.write_line(f"\n[green]✓ Generated {len(problems)} targeted problems![/green]\n")
                self._generated_problems = problems
                lines = []
                for i, p in enumerate(problems):
                    pid = self.app.problem_repo.create(p.to_db())
                    p.id = pid
                    lines.append(f"  {i+1}. [{p.difficulty.value.upper()}] {p.title}")
                    lines.append(f"     [dim]{', '.join(p.tags[:4])}[/dim]")
                self.query_one("#jd-problem-list", Static).update("\n".join(lines))
            else:
                stream.show_error("Could not generate problems. Check LLM connection.")
        except Exception as e:
            stream.show_error(f"Error: {e}")
