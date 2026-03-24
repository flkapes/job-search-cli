"""Job description screen — paste JD, AI generates practical problems or interview questions."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static, Tab, Tabs, TextArea

from codepractice.tui.widgets.streaming_output import StreamingOutput

_QUESTION_TYPES = ["technical", "behavioural", "system_design", "conceptual", "situational"]


class QuestionDetailModal(ModalScreen):
    """Modal showing a freeform interview question with follow-ups and a draft answer area."""

    DEFAULT_CSS = """
    QuestionDetailModal {
        align: center middle;
    }

    QuestionDetailModal #qd-container {
        width: 80%;
        height: 80%;
        background: #161b22;
        border: solid #58a6ff;
        padding: 1 2;
    }

    QuestionDetailModal #qd-close-bar {
        height: 3;
        dock: bottom;
        border-top: solid #30363d;
        padding: 0 2;
    }
    """

    def __init__(self, question: dict, question_hash: str, source_type: str = "jd", **kwargs):
        super().__init__(**kwargs)
        self._question = question
        self._question_hash = question_hash
        self._source_type = source_type

    def compose(self) -> ComposeResult:
        q = self._question
        from textual.containers import Vertical
        with Vertical(id="qd-container"):
            yield Label(f"[bold #58a6ff]{q.get('type', 'Question').upper()}[/bold #58a6ff]")
            yield Label(f"\n[bold]{q.get('question', '')}[/bold]\n")
            follow_ups = q.get("follow_ups", [])
            if follow_ups:
                yield Label("[dim]Follow-up questions:[/dim]")
                for fu in follow_ups:
                    yield Label(f"  • {fu}", classes="hint-text")
            yield Label("\n[bold]Your Draft Answer[/bold]")
            yield TextArea("", id="qd-draft")
            with Horizontal(id="qd-close-bar"):
                yield Button("Save & Close", id="btn-qd-save", classes="primary-btn")
                yield Button("Close", id="btn-qd-close", classes="secondary-btn")

    def on_mount(self) -> None:
        # Load existing draft
        try:
            from codepractice.db.repositories.question_drafts import QuestionDraftsRepository
            repo = QuestionDraftsRepository(self.app.db)
            draft = repo.get_draft(self._question_hash)
            if draft:
                self.query_one("#qd-draft", TextArea).load_text(draft["draft_text"])
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("btn-qd-save", "btn-qd-close"):
            if event.button.id == "btn-qd-save":
                try:
                    from codepractice.db.repositories.question_drafts import (
                        QuestionDraftsRepository,
                    )
                    text = self.query_one("#qd-draft", TextArea).text
                    repo = QuestionDraftsRepository(self.app.db)
                    repo.save_draft(self._question_hash, self._source_type, text)
                except Exception:
                    pass
            self.dismiss()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()


class JobDescContent(Widget):
    """Paste a job description → AI generates role-specific practice or interview questions."""

    DEFAULT_CSS = """
    JobDescContent {
        height: 1fr;
        padding: 0 1;
    }
    """

    _generated_problems: list = []
    _freeform_questions: list = []
    _active_tab: str = "coding"

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("[bold #58a6ff]💼 Job Description Prep[/bold #58a6ff]")
            yield Static(
                "[#8b949e]Paste a job description below. The AI will analyze the required skills "
                "and generate practical coding problems or freeform interview questions.[/#8b949e]\n"
            )

            with Horizontal():
                yield Input(placeholder="Company name (optional)", id="jd-company")
                yield Input(placeholder="Role title (optional)", id="jd-role")

            yield Label("[bold]Job Description[/bold]")
            yield TextArea("", id="jd-input")

            yield Tabs(
                Tab("💻 Coding Problems", id="tab-coding"),
                Tab("🗣 Interview Questions", id="tab-interview"),
                id="jd-tabs",
            )

            # Coding problems panel
            with Horizontal(id="panel-coding"):
                yield Button("🎯 Generate Problems", id="btn-gen-jd", classes="primary-btn")
                yield Label("  Problems: ", id="jd-count-label")
                yield Select(
                    [("3", "3"), ("5", "5"), ("8", "8")],
                    value="5",
                    id="jd-count",
                )
            yield Label("\n[bold]Analysis & Problems[/bold]", classes="panel-title", id="coding-output-label")
            yield StreamingOutput(id="jd-output")
            yield Static("", id="jd-problem-list")

            # Interview questions panel (hidden by default)
            with Horizontal(id="panel-interview"):
                yield Button("🗣 Generate Questions", id="btn-gen-questions", classes="primary-btn")
                yield Label("  Count: ")
                yield Select(
                    [("3", "3"), ("5", "5"), ("8", "8")],
                    value="5",
                    id="question-count",
                )
            yield DataTable(id="questions-table")

    def on_mount(self) -> None:
        self._show_tab("coding")
        table = self.query_one("#questions-table", DataTable)
        table.add_columns("Type", "Question", "Follow-ups")

    def _show_tab(self, tab: str) -> None:
        self._active_tab = tab
        for widget_id, show_on in (
            ("panel-coding", "coding"),
            ("jd-output", "coding"),
            ("jd-problem-list", "coding"),
            ("coding-output-label", "coding"),
            ("panel-interview", "interview"),
            ("questions-table", "interview"),
        ):
            try:
                self.query_one(f"#{widget_id}").display = tab == show_on
            except Exception:
                pass

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tab.id == "tab-coding":
            self._show_tab("coding")
        elif event.tab.id == "tab-interview":
            self._show_tab("interview")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-gen-jd":
            self._generate()
        elif event.button.id == "btn-gen-questions":
            self._generate_questions()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        idx = event.cursor_row
        if 0 <= idx < len(self._freeform_questions):
            q = self._freeform_questions[idx]
            import hashlib
            qhash = hashlib.sha256(q["question"].encode()).hexdigest()[:16]
            self.app.push_screen(QuestionDetailModal(q, qhash, source_type="jd"))

    def _generate(self) -> None:
        jd_text = self.query_one("#jd-input", TextArea).text
        if not jd_text.strip():
            self.query_one("#jd-output", StreamingOutput).show_error(
                "Please paste a job description first."
            )
            return

        company = self.query_one("#jd-company", Input).value
        count = int(self.query_one("#jd-count", Select).value or "5")

        stream = self.query_one("#jd-output", StreamingOutput)
        stream.clear()
        stream.show_info(
            f"Analyzing job description{' for ' + company if company else ''}..."
        )

        # Save JD
        try:
            from codepractice.db.database import get_db
            db = get_db()
            with db.get_connection() as conn:
                conn.execute(
                    "INSERT INTO job_descriptions (company_name, role_title, jd_text) VALUES (?,?,?)",
                    (company, self.query_one("#jd-role", Input).value, jd_text),
                )
        except Exception:
            pass

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

    def _generate_questions(self) -> None:
        jd_text = self.query_one("#jd-input", TextArea).text
        if not jd_text.strip():
            return

        count = int(self.query_one("#question-count", Select).value or "5")
        table = self.query_one("#questions-table", DataTable)
        table.clear()

        try:
            from codepractice.llm.services.problem_generator import ProblemGeneratorService
            gen = ProblemGeneratorService(self.app.llm)
            questions = gen.generate_freeform_questions(
                source="jd",
                text=jd_text,
                question_types=["technical", "behavioural", "system_design"],
                count=count,
            )
            self._freeform_questions = questions
            for q in questions:
                follow_ups = len(q.get("follow_ups", []))
                table.add_row(
                    q.get("type", "general"),
                    q.get("question", "")[:80],
                    str(follow_ups),
                )
        except Exception:
            self._freeform_questions = []
