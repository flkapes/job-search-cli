"""Resume drill — paste resume, AI generates targeted practice problems or interview questions."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, Select, Static, Tab, Tabs, TextArea

from codepractice.tui.widgets.streaming_output import StreamingOutput


class ResumeDrillContent(Widget):
    """Paste resume → AI generates personalized problems or freeform interview questions."""

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

    _generated_problems: list = []
    _freeform_questions: list = []

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("[bold #58a6ff]📄 Resume Drill[/bold #58a6ff]")
            yield Static(
                "[#8b949e]Paste your resume or project descriptions below. "
                "The AI will generate practice problems tailored to your experience, "
                "or freeform interview questions based on your projects.[/#8b949e]\n"
            )

            yield Label("[bold]Your Resume / Projects[/bold]")
            yield TextArea(
                "",
                id="resume-input",
                language=None,
            )

            yield Tabs(
                Tab("💻 Coding Problems", id="tab-resume-coding"),
                Tab("🗣 Interview Questions", id="tab-resume-interview"),
                id="resume-tabs",
            )

            # Coding problems panel
            with Horizontal(id="panel-resume-coding"):
                yield Select(
                    [(d, d) for d in ("easy", "medium", "hard")],
                    value="medium",
                    id="resume-difficulty",
                )
                yield Button("🔍 Analyze & Generate", id="btn-generate-resume", classes="primary-btn")
                yield Button("Load Saved Resume", id="btn-load-resume", classes="secondary-btn")

            yield Label("\n[bold]Generated Problems[/bold]", classes="panel-title", id="coding-problems-label")
            yield StreamingOutput(id="resume-output")
            yield Static("", id="resume-problem-list")

            # Interview questions panel (hidden by default)
            with Horizontal(id="panel-resume-interview"):
                yield Button("🗣 Generate Questions", id="btn-gen-resume-questions", classes="primary-btn")
                yield Label("  Count: ")
                yield Select(
                    [("3", "3"), ("5", "5"), ("8", "8")],
                    value="5",
                    id="resume-question-count",
                )
            yield DataTable(id="resume-questions-table")

    def on_mount(self) -> None:
        self._show_tab("coding")
        table = self.query_one("#resume-questions-table", DataTable)
        table.add_columns("Type", "Question", "Follow-ups")

        # Load saved resume if exists
        try:
            profile = self.app.profile_repo.get()
            if profile and profile.get("resume_text"):
                self.query_one("#resume-input", TextArea).load_text(profile["resume_text"])
        except Exception:
            pass

    def _show_tab(self, tab: str) -> None:
        for widget_id, show_on in (
            ("panel-resume-coding", "coding"),
            ("resume-output", "coding"),
            ("resume-problem-list", "coding"),
            ("coding-problems-label", "coding"),
            ("panel-resume-interview", "interview"),
            ("resume-questions-table", "interview"),
        ):
            try:
                self.query_one(f"#{widget_id}").display = tab == show_on
            except Exception:
                pass

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tab.id == "tab-resume-coding":
            self._show_tab("coding")
        elif event.tab.id == "tab-resume-interview":
            self._show_tab("interview")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-generate-resume":
            self._generate_problems()
        elif event.button.id == "btn-load-resume":
            self._load_saved_resume()
        elif (event.button.id or "").startswith("resume-problem-"):
            idx = int(event.button.id.split("-")[-1])
            self._start_problem(idx)
        elif event.button.id == "btn-gen-resume-questions":
            self._generate_questions()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "resume-questions-table":
            idx = event.cursor_row
            if 0 <= idx < len(self._freeform_questions):
                q = self._freeform_questions[idx]
                import hashlib
                qhash = hashlib.sha256(q["question"].encode()).hexdigest()[:16]
                from codepractice.tui.screens.job_desc import QuestionDetailModal
                self.app.push_screen(QuestionDetailModal(q, qhash, source_type="resume"))

    def _load_saved_resume(self) -> None:
        try:
            profile = self.app.profile_repo.get()
            if profile and profile.get("resume_text"):
                self.query_one("#resume-input", TextArea).load_text(profile["resume_text"])
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

                from codepractice.llm.services.problem_generator import ProblemGeneratorService
                gen = ProblemGeneratorService(self.app.llm)
                problems = gen.generate_from_resume(parsed, difficulty, count=5)

                if problems:
                    stream.write_line(f"\n[green]✓ Generated {len(problems)} problems![/green]\n")
                    problem_list = self.query_one("#resume-problem-list", Static)
                    lines = []
                    self._generated_problems = problems
                    for i, p in enumerate(problems):
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

    def _generate_questions(self) -> None:
        resume_text = self.query_one("#resume-input", TextArea).text
        if not resume_text.strip():
            return

        count = int(self.query_one("#resume-question-count", Select).value or "5")
        table = self.query_one("#resume-questions-table", DataTable)
        table.clear()

        try:
            from codepractice.llm.services.problem_generator import ProblemGeneratorService
            gen = ProblemGeneratorService(self.app.llm)
            questions = gen.generate_freeform_questions(
                source="resume",
                text=resume_text,
                question_types=["technical", "behavioural", "situational"],
                count=count,
            )
            self._freeform_questions = questions
            for q in questions:
                follow_ups_count = len(q.get("follow_ups", []))
                table.add_row(
                    q.get("type", "general"),
                    q.get("question", "")[:80],
                    str(follow_ups_count),
                )
        except Exception:
            self._freeform_questions = []

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
