"""Resume drill — paste resume, AI generates targeted practice problems."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Label, Select, Static, TextArea

from codepractice.tui.widgets.streaming_output import StreamingOutput


class ResumeDrillContent(Widget):
    """Paste resume → AI generates personalized problems."""

    DEFAULT_CSS = """
    ResumeDrillContent {
        height: 1fr;
        padding: 0 1;
    }

    ResumeDrillContent #resume-input-area {
        height: 14;
    }

    ResumeDrillContent #generated-problems {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("[bold #58a6ff]📄 Resume Drill[/bold #58a6ff]")
            yield Static(
                "[#8b949e]Paste your resume or project descriptions below. "
                "The AI will generate practice problems tailored to your experience, "
                "helping you speak confidently about your work in interviews.[/#8b949e]\n"
            )

            yield Label("[bold]Your Resume / Projects[/bold]")
            yield TextArea(
                "",
                id="resume-input",
                language=None,
            )

            with Horizontal():
                yield Select(
                    [(d, d) for d in ("easy", "medium", "hard")],
                    value="medium",
                    id="resume-difficulty",
                )
                yield Button("🔍 Analyze & Generate", id="btn-generate-resume", classes="primary-btn")
                yield Button("Load Saved Resume", id="btn-load-resume", classes="secondary-btn")

            yield Label("\n[bold]Generated Problems[/bold]", classes="panel-title")
            yield StreamingOutput(id="resume-output")

            yield Static("", id="resume-problem-list")

    def on_mount(self) -> None:
        # Load saved resume if exists
        try:
            profile = self.app.profile_repo.get()
            if profile and profile.get("resume_text"):
                self.query_one("#resume-input", TextArea).text = profile["resume_text"]
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-generate-resume":
            self._generate_problems()
        elif event.button.id == "btn-load-resume":
            self._load_saved_resume()
        elif (event.button.id or "").startswith("resume-problem-"):
            idx = int(event.button.id.split("-")[-1])
            self._start_problem(idx)

    def _load_saved_resume(self) -> None:
        try:
            profile = self.app.profile_repo.get()
            if profile and profile.get("resume_text"):
                self.query_one("#resume-input", TextArea).text = profile["resume_text"]
        except Exception:
            pass

    def _generate_problems(self) -> None:
        resume_text = self.query_one("#resume-input", TextArea).text
        if not resume_text.strip():
            stream = self.query_one("#resume-output", StreamingOutput)
            stream.show_error("Please paste your resume text first.")
            return

        difficulty = str(self.query_one("#resume-difficulty", Select).value)
        stream = self.query_one("#resume-output", StreamingOutput)
        stream.clear()
        stream.show_info("Analyzing your resume and generating targeted problems...")

        # Save resume
        try:
            if self.app.profile_repo.exists():
                self.app.profile_repo.update({"resume_text": resume_text})
            else:
                self.app.profile_repo.create({"resume_text": resume_text})
        except Exception:
            pass

        # Parse resume via LLM
        try:
            from codepractice.llm.services.chat_service import ChatService
            chat = ChatService(self.app.llm, self.app.chat_repo)
            parsed = chat.analyze_resume(resume_text)

            if parsed:
                self.app.profile_repo.update({"resume_parsed": parsed})
                skills = parsed.get("skills", [])
                stream.write_line(f"[green]✓ Found skills:[/green] {', '.join(skills[:10])}")

                # Generate problems
                from codepractice.llm.services.problem_generator import ProblemGeneratorService
                gen = ProblemGeneratorService(self.app.llm)
                problems = gen.generate_from_resume(parsed, difficulty, count=5)

                if problems:
                    stream.write_line(f"\n[green]✓ Generated {len(problems)} problems![/green]\n")
                    problem_list = self.query_one("#resume-problem-list", Static)
                    lines = []
                    self._generated_problems = problems
                    for i, p in enumerate(problems):
                        # Save to DB
                        pid = self.app.problem_repo.create(p.to_db())
                        p.id = pid
                        diff_badge = {"easy": "[green]EASY[/green]", "medium": "[yellow]MED[/yellow]", "hard": "[red]HARD[/red]"}.get(p.difficulty.value, p.difficulty.value)
                        lines.append(f"  {i+1}. {diff_badge} {p.title}")
                    problem_list.update("\n".join(lines))
                else:
                    stream.show_error("Could not generate problems. Check your LLM connection.")
            else:
                stream.show_error("Could not parse resume. Try with more content.")
        except Exception as e:
            stream.show_error(f"Error: {e}")

    _generated_problems: list = []

    def _start_problem(self, idx: int) -> None:
        if 0 <= idx < len(self._generated_problems):
            problem = self._generated_problems[idx]
            from codepractice.tui.screens.practice import PracticeContent
            content = self.app.query_one("#content")
            content.remove_children()
            widget = PracticeContent()
            content.mount(widget)
            widget._problem = problem
            widget.call_later(widget._show_problem)
