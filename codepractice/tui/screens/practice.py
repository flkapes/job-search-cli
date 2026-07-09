"""Practice session — 3-phase state machine: problem → code → feedback."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from enum import Enum

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, Select, Static

from codepractice.core.models import Problem
from codepractice.core.spaced_repetition import get_due_problems, update_schedule
from codepractice.tui.widgets.code_editor import CodeEditor
from codepractice.tui.widgets.problem_card import ProblemCard
from codepractice.tui.widgets.streaming_output import StreamingOutput
from codepractice.utils.languages import available_languages


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

    /* Stable region for streamed feedback — content scrolls inside instead
       of the panel growing and relayouting the screen on every line. */
    PracticeContent #feedback-stream {
        height: 1fr;
        max-height: 100%;
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
        Binding("b", "toggle_bookmark", "Bookmark", show=True),
        Binding("ctrl+enter", "submit_code", "Submit", show=False),
        Binding("escape", "back_to_problem", "Back", show=False),
    ]

    current_phase: reactive[str] = reactive("loading")
    _problem: Problem | None = None
    _session_id: int | None = None
    _code_start_time: float = 0
    _hints_used: int = 0
    _review_mode: bool = False
    _last_attempt_id: int | None = None
    _init_session_type: str = "free"
    _drill_category: str | None = None
    _drill_subcategory: str | None = None
    _drill_difficulty: str | None = None
    _simulation_mode: bool = False
    _simulation_duration_sec: int = 0
    _simulation_deadline: datetime | None = None
    _simulation_locked: bool = False
    _peek_attempts: int = 0
    _sim_problem_index: int = 0
    _language: str = "python"

    def _effective_difficulty(self) -> str | None:
        """Difficulty for the next problem — simulations alternate medium/hard."""
        if self._simulation_mode:
            difficulty = "medium" if self._sim_problem_index % 2 == 0 else "hard"
            self._sim_problem_index += 1
            return difficulty
        return self._drill_difficulty

    def __init__(
        self,
        review_mode: bool = False,
        simulation_mode: bool = False,
        simulation_duration_sec: int = 1800,
        session_type: str | None = None,
        drill_category: str | None = None,
        drill_subcategory: str | None = None,
        drill_difficulty: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._review_mode = review_mode
        self._simulation_mode = simulation_mode
        self._simulation_duration_sec = simulation_duration_sec if simulation_mode else 0
        if simulation_mode:
            self._init_session_type = "interview_simulation"
            # Simulations mirror real interviews: DSA only, medium/hard mix.
            self._drill_category = "dsa"
        elif session_type:
            self._init_session_type = session_type
        if drill_category:
            self._drill_category = drill_category
        if drill_subcategory:
            self._drill_subcategory = drill_subcategory
        if drill_difficulty:
            self._drill_difficulty = drill_difficulty

    def compose(self) -> ComposeResult:
        with Horizontal(id="practice-top-bar"):
            yield Label("🧪 [bold]Interview Simulation[/bold]" if self._simulation_mode else "⚡ [bold]Free Practice[/bold]", id="practice-title")
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
                yield Button("Finish Simulation", id="btn-finish-sim", classes="secondary-btn")

        # Phase: Coding (split pane)
        with Horizontal(id="phase-coding"):
            with VerticalScroll(id="coding-left"):
                yield ProblemCard(id="problem-mini")
            with Vertical(id="coding-right"):
                yield CodeEditor(id="code-editor")
                with Horizontal(classes="action-bar"):
                    yield Button("Submit [Ctrl+Enter]", id="btn-submit", classes="primary-btn")
                    yield Button("Back [Esc]", id="btn-back-problem", classes="secondary-btn")
                    yield Select(
                        [(spec.name, spec.id) for spec in available_languages()],
                        value=self._language,
                        id="language-select",
                        allow_blank=False,
                    )

        # Phase: Feedback
        with Vertical(id="phase-feedback"):
            yield Label("[bold]Evaluation[/bold]", classes="panel-title")
            yield Static("", id="test-results-panel")
            yield StreamingOutput(id="feedback-stream")
            yield Static("", id="diff-panel")
            with Horizontal(id="rating-bar"):
                yield Label("[dim]How hard was this for you?[/dim]  ")
                for i in range(1, 6):
                    yield Button(str(i), id=f"btn-rate-{i}", classes="secondary-btn")
                yield Button("Skip", id="btn-rate-skip", classes="secondary-btn")
            with Horizontal(classes="action-bar"):
                yield Button("Next Problem [N]", id="btn-next", classes="primary-btn")
                yield Button("Retry", id="btn-retry", classes="secondary-btn")
                yield Button("Dashboard [D]", id="btn-dashboard", classes="secondary-btn")

    def on_mount(self) -> None:
        # Hide all phases except loading
        self._show_phase("loading")
        # Start a session and load first problem
        self.call_later(self._init_session)
        self.set_interval(1.0, self._tick_timer)

    def _show_phase(self, phase: str) -> None:
        for pid in ("phase-loading", "phase-problem", "phase-coding", "phase-feedback"):
            widget = self.query_one(f"#{pid}")
            widget.display = pid == f"phase-{phase}"
        self.current_phase = phase
        if phase == "feedback":
            try:
                self.query_one("#diff-panel", Static).update("")
                self.query_one("#test-results-panel", Static).update("")
                self.query_one("#rating-bar").display = True
            except Exception:
                pass

    def _hide_rating_bar(self) -> None:
        try:
            self.query_one("#rating-bar").display = False
        except Exception:
            pass

    def _init_session(self) -> None:
        try:
            session_type = getattr(self, "_init_session_type", "free")
            metadata = {}
            if self._simulation_mode:
                self._simulation_deadline = datetime.now() + timedelta(seconds=self._simulation_duration_sec)
                metadata = {"duration_sec": self._simulation_duration_sec, "simulation_mode": True}
            self._session_id = self.app.session_repo.start_session(session_type, metadata=metadata)
        except Exception:
            self._session_id = None
        self._load_next_problem(
            category=self._drill_category,
            subcategory=self._drill_subcategory,
            difficulty=self._effective_difficulty(),
        )

    def _load_next_problem(
        self,
        category: str | None = None,
        difficulty: str | None = None,
        subcategory: str | None = None,
    ) -> None:
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
        problem_data = self.app.problem_repo.get_random(
            category=category, subcategory=subcategory, difficulty=difficulty
        )
        if problem_data:
            self._problem = Problem.from_db(problem_data)
            self._show_problem()
        else:
            # Try AI generation
            self._generate_ai_problem(category, difficulty, subcategory)

    def _generate_ai_problem(
        self,
        category: str | None,
        difficulty: str | None,
        subcategory: str | None = None,
    ) -> None:
        try:
            from codepractice.llm.services.problem_generator import ProblemGeneratorService
            gen = ProblemGeneratorService(self.app.llm)
            if category == "dsa":
                problem = gen.generate_dsa(subcategory or "two_pointers", difficulty or "medium")
            else:
                problem = gen.generate_python_fundamental(
                    "Python Fundamentals", subcategory or "vocabulary",
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

    # Categories whose problems are language-agnostic; python_fundamentals
    # problems are Python-specific by definition, so the selector locks there.
    _MULTI_LANGUAGE_CATEGORIES = ("dsa", "practical")

    def _show_problem(self) -> None:
        if not self._problem:
            return
        self.query_one("#problem-display", ProblemCard).load_problem(self._problem)
        self.query_one("#problem-mini", ProblemCard).load_problem(self._problem)
        hint_btn = self.query_one("#btn-hint", Button)
        finish_btn = self.query_one("#btn-finish-sim", Button)
        hint_btn.disabled = self._simulation_mode
        finish_btn.display = self._simulation_mode
        self._gate_language_selector()
        self._show_phase("problem")

    def _gate_language_selector(self) -> None:
        """Offer language choice only where the problem isn't language-specific."""
        try:
            selector = self.query_one("#language-select", Select)
            allowed = self._problem.category in self._MULTI_LANGUAGE_CATEGORIES
            selector.display = allowed and len(available_languages()) > 1
            if not allowed and self._language != "python":
                self._language = "python"
                selector.value = "python"
                self.query_one("#code-editor", CodeEditor).set_language("python")
        except Exception:
            pass

    # ── Actions ────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button.id
        if btn == "btn-start-coding":
            self._enter_coding()
        elif btn == "btn-skip" or btn == "btn-next":
            self.action_next_problem()
        elif btn == "btn-hint":
            self.action_show_hint()
        elif btn == "btn-finish-sim":
            self._finish_simulation()
        elif btn == "btn-submit":
            self.action_submit_code()
        elif btn == "btn-back-problem":
            self.action_back_to_problem()
        elif btn == "btn-retry":
            self._enter_coding()
        elif btn == "btn-dashboard":
            self.app._switch_content("dashboard")
        elif btn and btn.startswith("btn-rate-") and btn != "btn-rate-skip":
            try:
                rating = int(btn.split("-")[-1])
                if self._last_attempt_id:
                    self.app.session_repo.set_difficulty_rating(self._last_attempt_id, rating)
                self._hide_rating_bar()
            except Exception:
                pass
        elif btn == "btn-rate-skip":
            self._hide_rating_bar()

    def on_code_editor_code_submitted(self, event: CodeEditor.CodeSubmitted) -> None:
        self.action_submit_code()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "language-select" and event.value:
            self._language = str(event.value)
            try:
                self.query_one("#code-editor", CodeEditor).set_language(self._language)
            except Exception:
                pass

    def _enter_coding(self) -> None:
        self._code_start_time = time.time()
        editor = self.query_one("#code-editor", CodeEditor)
        editor.clear()
        try:
            editor.set_language(self._language)
        except Exception:
            pass
        self._show_phase("coding")
        editor.query_one("#code-input").focus()

    def _submit_code(self) -> None:
        # Prevent duplicate submissions once we have already left the coding phase.
        if self.current_phase != "coding":
            return

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

            verification_holder: dict = {"verification": None}
            problem, language = self._problem, self._language

            def evaluation_stream():
                # Runs lazily on the streaming worker thread: subprocess-based
                # verification and LLM tokens both stay off the UI thread.
                try:
                    verification = evaluator.verify(problem, code, language=language)
                    verification_holder["verification"] = verification
                    self.app.call_from_thread(self._show_test_results, verification)
                except Exception:
                    verification = None
                yield from evaluator.stream_evaluation(
                    problem, code, verification=verification, language=language
                )

            stream.stream_in_worker(
                evaluation_stream(),
                on_complete=lambda full_text: self._finish_evaluation(
                    full_text, verification_holder["verification"], code, elapsed
                ),
                on_error=lambda e: stream.show_error(f"Evaluation failed: {e}"),
            )
        except Exception as e:
            stream.show_error(f"Evaluation failed: {e}")

    def _finish_evaluation(self, full_text: str, verification, code: str, elapsed: int) -> None:
        """Post-stream bookkeeping — runs on the UI thread once tokens finish."""
        stream = self.query_one("#feedback-stream", StreamingOutput)
        try:
            # Parse score from response and record attempt
            from codepractice.llm.client import extract_json
            score_data = extract_json(full_text.split("\n")[-1]) if full_text else None
            score = float(score_data.get("score", 0.5)) if isinstance(score_data, dict) else 0.5
            passed = bool(score_data.get("passed", score >= 0.7)) if isinstance(score_data, dict) else score >= 0.7

            # Guardrails: the LLM can't pass code that fails its test cases
            try:
                from codepractice.utils.code_runner import clamp_score
                score, passed = clamp_score(score, passed, verification)
            except Exception:
                pass

            if self._session_id and self._problem and self._problem.id:
                self._last_attempt_id = self.app.session_repo.record_attempt({
                    "session_id": self._session_id,
                    "problem_id": self._problem.id,
                    "user_code": code,
                    "ai_feedback": full_text[:2000],
                    "ai_score": score,
                    "time_spent_sec": elapsed,
                    "hints_used": self._hints_used,
                    "passed": passed,
                    "language": self._language,
                })
                if passed:
                    self.app.problem_repo.increment_solved(self._problem.id)
                self.app.problem_repo.increment_shown(self._problem.id)
                # Update spaced-repetition schedule for this problem
                try:
                    update_schedule(self.app.db, self._problem.id, score)
                except Exception:
                    pass
                self._award_rewards(score, passed, elapsed)

            # Show optimized solution diff if score < 0.9
            try:
                from codepractice.utils.text_utils import (
                    extract_optimized_solution,
                    should_show_diff,
                )
                if should_show_diff(score) and full_text:
                    opt = extract_optimized_solution(full_text)
                    if opt:
                        diff_panel = self.query_one("#diff-panel", Static)
                        diff_panel.update(
                            "\n[bold #58a6ff]💡 Suggested Approach[/bold #58a6ff]\n"
                            + opt
                        )
            except Exception:
                pass

        except Exception as e:
            stream.show_error(f"Evaluation failed: {e}")

    def _award_rewards(self, score: float, passed: bool, elapsed: int) -> None:
        """Award XP and surface achievement unlock toasts for the last attempt."""
        try:
            from codepractice.core.gamification import award_attempt, level_for_xp
            xp, new_achievements = award_attempt(
                self.app.gamification_repo,
                self.app.session_repo,
                self._problem,
                self._last_attempt_id,
                score,
                passed,
                time_spent_sec=elapsed,
                hints_used=self._hints_used,
            )
            if xp:
                info = level_for_xp(self.app.gamification_repo.total_xp())
                self.notify(
                    f"+{xp} XP  —  Level {info.level}: {info.title}",
                    title="XP earned",
                    timeout=4,
                )
            for a in new_achievements:
                self.notify(
                    f"{a.icon} {a.name} — {a.description}",
                    title="Achievement unlocked!",
                    severity="information",
                    timeout=8,
                )
        except Exception:
            pass

    def _show_test_results(self, verification) -> None:
        """Render the per-test-case verification table in the feedback phase."""
        panel = self.query_one("#test-results-panel", Static)
        if verification is None or verification.total == 0:
            panel.update("")
            return
        lines = ["[bold]Test Cases[/bold]"]
        for i, r in enumerate(verification.results, 1):
            if not r.comparable:
                lines.append(f"  [dim]○ Case {i}: not verifiable via stdout[/dim]")
            elif r.passed:
                lines.append(f"  [#3fb950]✓ Case {i}: passed[/#3fb950] [dim]({r.runtime_ms:.0f}ms)[/dim]")
            elif r.error:
                lines.append(f"  [#f85149]✗ Case {i}: {r.error}[/#f85149]")
            else:
                lines.append(
                    f"  [#f85149]✗ Case {i}: expected [bold]{r.expected[:60]}[/bold], "
                    f"got [bold]{r.actual[:60] or '(nothing)'}[/bold][/#f85149]"
                )
        if verification.comparable:
            color = "#3fb950" if verification.all_passed else "#f85149"
            lines.append(
                f"  [{color}]{verification.passed}/{verification.comparable} verified cases passed[/{color}]"
            )
        panel.update("\n".join(lines))

    def action_show_hint(self) -> None:
        if self._simulation_mode:
            self._peek_attempts += 1
            return
        if self.current_phase == "problem":
            card = self.query_one("#problem-display", ProblemCard)
        elif self.current_phase == "coding":
            card = self.query_one("#problem-mini", ProblemCard)
        else:
            return
        hint = card.show_next_hint()
        if hint:
            self._hints_used += 1

    def action_toggle_bookmark(self) -> None:
        try:
            card = self.query_one("#problem-display", ProblemCard)
            state = card.toggle_bookmark()
            if state is not None:
                self.query_one("#problem-mini", ProblemCard)._refresh_bookmark_button()
                self.notify(
                    "Bookmarked — find it in My Library" if state else "Bookmark removed",
                    timeout=3,
                )
        except Exception:
            pass

    def action_next_problem(self) -> None:
        if self._simulation_locked:
            return
        # Preserve drill filters so "Next" stays inside the chosen track
        self._load_next_problem(
            category=self._drill_category,
            subcategory=self._drill_subcategory,
            difficulty=self._effective_difficulty(),
        )

    def action_back_to_problem(self) -> None:
        if self.current_phase == "coding":
            self._show_phase("problem")

    def action_submit_code(self) -> None:
        if self.current_phase != "coding" or self._simulation_locked:
            return
        self._submit_code()

    def _timer_state(self) -> tuple[str, str]:
        if not self._simulation_mode or not self._simulation_deadline:
            return "", "white"
        remaining = int((self._simulation_deadline - datetime.now()).total_seconds())
        if remaining <= 0:
            return "00:00", "red"
        mm, ss = divmod(remaining, 60)
        if remaining <= 300:
            color = "red"
        elif remaining <= 900:
            color = "yellow"
        else:
            color = "green"
        return f"{mm:02d}:{ss:02d}", color

    def _tick_timer(self) -> None:
        if not self._simulation_mode:
            return
        text, color = self._timer_state()
        self.query_one("#timer-label", Label).update(f"[{color}]⏱ {text}[/{color}]")
        if text == "00:00" and not self._simulation_locked:
            self._finish_simulation()

    def _finish_simulation(self) -> None:
        if not self._simulation_mode or self._simulation_locked:
            return
        self._simulation_locked = True
        if self._session_id:
            card = self.app.session_repo.get_scorecard(self._session_id)
            attempted = int(card.get("attempted", 0))
            solved = int(card.get("solved", 0))
            self.app.session_repo.end_session(
                self._session_id,
                total=attempted,
                solved=solved,
                notes=f"peek_attempts={self._peek_attempts}",
            )
            self._show_scorecard(card)

    def _show_scorecard(self, card: dict) -> None:
        from codepractice.core.difficulty import apply_peek_penalty

        raw_avg = float(card.get("avg_score", 0.0))
        adjusted = apply_peek_penalty(raw_avg, self._peek_attempts)
        avg_pct = int(adjusted * 100)
        verdict = "PASS" if avg_pct >= 70 else "FAIL"
        lines = [
            "[bold]Interview Simulation Complete[/bold]",
            f"Attempted: {card.get('attempted', 0)}",
            f"Solved: {card.get('solved', 0)}",
            f"Average score: {int(raw_avg * 100)}%",
        ]
        if self._peek_attempts:
            lines.append(
                f"Hint peeks: {self._peek_attempts} "
                f"(-{self._peek_attempts * 5}% → final {avg_pct}%)"
            )
        lines += [
            f"Verdict: [bold]{verdict}[/bold]",
            "Category breakdown:",
        ]
        for row in card.get("category_breakdown", []):
            lines.append(
                f"- {row.get('category')}: {row.get('solved')}/{row.get('attempted')} ({int(float(row.get('avg_score', 0))*100)}%)"
            )
        self.query_one("#feedback-stream", StreamingOutput).update("\n".join(lines))
        self._show_phase("feedback")
