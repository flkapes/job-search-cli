"""Practice session — 3-phase state machine: problem → code → feedback."""

from __future__ import annotations

import time
from enum import Enum

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, Static

from codepractice.core.models import Problem
from codepractice.core.spaced_repetition import get_due_problems, update_schedule
from codepractice.tui.widgets.code_editor import CodeEditor
from codepractice.tui.widgets.problem_card import ProblemCard
from codepractice.tui.widgets.streaming_output import StreamingOutput


class Phase(str, Enum):
    PROBLEM = "problem"
    CODING = "coding"
    FEEDBACK = "feedback"
    LOADING = "loading"


class PracticeContent(Widget):
    """Active problem session — show problem, capture code, AI evaluation."""

    DEFAULT_CSS = """
    PracticeContent {
        height: 1fr;
    }

    PracticeContent #practice-top-bar {
        height: 3;
        background: #1c2128;
        padding: 0 2;
        border-bottom: solid #30363d;
    }

    PracticeContent #phase-problem {
        height: 1fr;
    }

    PracticeContent #phase-coding {
        height: 1fr;
    }

    PracticeContent #coding-left {
        width: 1fr;
        border-right: solid #30363d;
    }

    PracticeContent #coding-right {
        width: 1fr;
    }

    PracticeContent #phase-feedback {
        height: 1fr;
        padding: 1;
    }

    PracticeContent #phase-loading {
        height: 1fr;
        content-align: center middle;
    }

    PracticeContent .action-bar {
        height: 3;
        background: #161b22;
        border-top: solid #30363d;
        padding: 0 2;
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("h", "show_hint", "Hint", show=True),
        Binding("n", "next_problem", "Next", show=True),
        Binding("escape", "back_to_problem", "Back", show=False),
    ]

    current_phase: reactive[str] = reactive("loading")
    _problem: Problem | None = None
    _session_id: int | None = None
    _code_start_time: float = 0
    _hints_used: int = 0
    _review_mode: bool = False

    def __init__(self, review_mode: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._review_mode = review_mode

    def compose(self) -> ComposeResult:
        with Horizontal(id="practice-top-bar"):
            yield Label("⚡ [bold]Free Practice[/bold]", id="practice-title")
            yield Label("", id="timer-label")

        # Phase: Loading
        yield Static("[bold #58a6ff]Generating problem...[/bold #58a6ff]", id="phase-loading")

        # Phase: Problem display
        with VerticalScroll(id="phase-problem"):
            yield ProblemCard(id="problem-display")
            with Horizontal(classes="action-bar"):
                yield Button("Start Coding [Enter]", id="btn-start-coding", classes="primary-btn")
                yield Button("Skip [N]", id="btn-skip", classes="secondary-btn")
                yield Button("Hint [H]", id="btn-hint", classes="secondary-btn")

        # Phase: Coding (split pane)
        with Horizontal(id="phase-coding"):
            with VerticalScroll(id="coding-left"):
                yield ProblemCard(id="problem-mini")
            with Vertical(id="coding-right"):
                yield CodeEditor(id="code-editor")
                with Horizontal(classes="action-bar"):
                    yield Button("Submit [Ctrl+Enter]", id="btn-submit", classes="primary-btn")
                    yield Button("Back [Esc]", id="btn-back-problem", classes="secondary-btn")

        # Phase: Feedback
        with Vertical(id="phase-feedback"):
            yield Label("[bold]Evaluation[/bold]", classes="panel-title")
            yield StreamingOutput(id="feedback-stream")
            with Horizontal(classes="action-bar"):
                yield Button("Next Problem [N]", id="btn-next", classes="primary-btn")
                yield Button("Retry", id="btn-retry", classes="secondary-btn")
                yield Button("Dashboard [D]", id="btn-dashboard", classes="secondary-btn")

    def on_mount(self) -> None:
        # Hide all phases except loading
        self._show_phase("loading")
        # Start a session and load first problem
        self.call_later(self._init_session)

    def _show_phase(self, phase: str) -> None:
        for pid in ("phase-loading", "phase-problem", "phase-coding", "phase-feedback"):
            widget = self.query_one(f"#{pid}")
            widget.display = pid == f"phase-{phase}"
        self.current_phase = phase

    def _init_session(self) -> None:
        try:
            self._session_id = self.app.session_repo.start_session("free")
        except Exception:
            self._session_id = None
        self._load_next_problem()

    def _load_next_problem(self, category: str | None = None, difficulty: str | None = None) -> None:
        self._show_phase("loading")
        self._hints_used = 0

        # In review mode, prioritise due problems from the spaced-repetition queue
        if self._review_mode and not category:
            due_ids = get_due_problems(self.app.db, n=1)
            if due_ids:
                problem_data = self.app.problem_repo.get_by_id(due_ids[0])
                if problem_data:
                    self._problem = Problem.from_db(problem_data)
                    self._show_problem()
                    return

        # Try to get a problem from the database
        problem_data = self.app.problem_repo.get_random(category=category, difficulty=difficulty)
        if problem_data:
            self._problem = Problem.from_db(problem_data)
            self._show_problem()
        else:
            # Try AI generation
            self._generate_ai_problem(category, difficulty)

    def _generate_ai_problem(self, category: str | None, difficulty: str | None) -> None:
        try:
            from codepractice.llm.services.problem_generator import ProblemGeneratorService
            gen = ProblemGeneratorService(self.app.llm)
            problem = gen.generate_python_fundamental(
                "Python Fundamentals", category or "vocabulary",
                difficulty or "medium"
            )
            if problem:
                # Save to DB
                pid = self.app.problem_repo.create(problem.to_db())
                problem.id = pid
                self._problem = problem
                self._show_problem()
                return
        except Exception:
            pass

        # Show fallback
        self._problem = Problem(
            title="No problems available",
            description="No problems could be loaded. Check your LLM connection or add problem data files.",
            category="python_fundamentals",
        )
        self._show_problem()

    def _show_problem(self) -> None:
        if not self._problem:
            return
        self.query_one("#problem-display", ProblemCard).load_problem(self._problem)
        self.query_one("#problem-mini", ProblemCard).load_problem(self._problem)
        self._show_phase("problem")

    # ── Actions ────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button.id
        if btn == "btn-start-coding":
            self._enter_coding()
        elif btn == "btn-skip" or btn == "btn-next":
            self.action_next_problem()
        elif btn == "btn-hint":
            self.action_show_hint()
        elif btn == "btn-submit":
            self._submit_code()
        elif btn == "btn-back-problem":
            self.action_back_to_problem()
        elif btn == "btn-retry":
            self._enter_coding()
        elif btn == "btn-dashboard":
            self.app._switch_content("dashboard")

    def on_code_editor_code_submitted(self, event: CodeEditor.CodeSubmitted) -> None:
        self._submit_code()

    def _enter_coding(self) -> None:
        self._code_start_time = time.time()
        editor = self.query_one("#code-editor", CodeEditor)
        editor.clear()
        self._show_phase("coding")
        editor.query_one("#code-input").focus()

    def _submit_code(self) -> None:
        code = self.query_one("#code-editor", CodeEditor).get_code()
        if not code.strip():
            return

        elapsed = int(time.time() - self._code_start_time)
        self._show_phase("feedback")

        stream = self.query_one("#feedback-stream", StreamingOutput)
        stream.clear()
        stream.show_info(f"Evaluating your solution... (time: {elapsed}s)")

        # Run evaluation in a worker thread
        self._evaluate_code(code, elapsed)

    def _evaluate_code(self, code: str, elapsed: int) -> None:
        stream = self.query_one("#feedback-stream", StreamingOutput)
        try:
            from codepractice.llm.services.answer_evaluator import AnswerEvaluatorService
            evaluator = AnswerEvaluatorService(self.app.llm)
            full_text = stream.stream_sync(
                evaluator.stream_evaluation(self._problem, code)
            )

            # Parse score from response and record attempt
            from codepractice.llm.client import extract_json
            score_data = extract_json(full_text.split("\n")[-1]) if full_text else None
            score = float(score_data.get("score", 0.5)) if isinstance(score_data, dict) else 0.5
            passed = bool(score_data.get("passed", score >= 0.7)) if isinstance(score_data, dict) else score >= 0.7

            if self._session_id and self._problem and self._problem.id:
                self.app.session_repo.record_attempt({
                    "session_id": self._session_id,
                    "problem_id": self._problem.id,
                    "user_code": code,
                    "ai_feedback": full_text[:2000],
                    "ai_score": score,
                    "time_spent_sec": elapsed,
                    "hints_used": self._hints_used,
                    "passed": passed,
                })
                if passed:
                    self.app.problem_repo.increment_solved(self._problem.id)
                self.app.problem_repo.increment_shown(self._problem.id)
                # Update spaced-repetition schedule for this problem
                try:
                    update_schedule(self.app.db, self._problem.id, score)
                except Exception:
                    pass

        except Exception as e:
            stream.show_error(f"Evaluation failed: {e}")

    def action_show_hint(self) -> None:
        if self.current_phase == "problem":
            card = self.query_one("#problem-display", ProblemCard)
        elif self.current_phase == "coding":
            card = self.query_one("#problem-mini", ProblemCard)
        else:
            return
        hint = card.show_next_hint()
        if hint:
            self._hints_used += 1

    def action_next_problem(self) -> None:
        self._load_next_problem()

    def action_back_to_problem(self) -> None:
        if self.current_phase == "coding":
            self._show_phase("problem")
