"""Root Textual App — screen router, dependency injection, global keybindings."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal

from codepractice.db.database import get_db
from codepractice.db.repositories import (
    ChatHistoryRepository,
    LearningPlanRepository,
    ProblemRepository,
    ProfileRepository,
    SessionRepository,
)
from codepractice.llm.client import LLMClient, get_client
from codepractice.tui.widgets.header import AppHeader
from codepractice.tui.widgets.sidebar import SidebarNav

CSS_PATH = Path(__file__).parent / "theme.tcss"


class CodePracticeApp(App):
    """The main TUI application."""

    TITLE = "CodePractice"
    SUB_TITLE = "AI-Powered Coding Practice"
    CSS_PATH = CSS_PATH

    BINDINGS = [
        Binding("d", "goto('dashboard')", "Dashboard", show=True),
        Binding("p", "goto('practice')", "Practice", show=False),
        Binding("r", "goto('review')", "Review", show=False),
        Binding("t", "goto('python_track')", "Python Track", show=False),
        Binding("a", "goto('dsa_training')", "DSA", show=False),
        Binding("l", "goto('learning_plan')", "Learn", show=False),
        Binding("c", "goto('chat')", "Chat", show=False),
        Binding("s", "goto('profile')", "Settings", show=False),
        Binding("q", "quit", "Quit", show=True),
    ]

    # ── Shared state ───────────────────────────────────────────────────────────

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = get_db()
        self._db = self.db  # backward-compat alias
        self.problem_repo = ProblemRepository(self.db)
        self.session_repo = SessionRepository(self.db)
        self.profile_repo = ProfileRepository(self.db)
        self.plan_repo = LearningPlanRepository(self.db)
        self.chat_repo = ChatHistoryRepository(self.db)
        self._llm: LLMClient | None = None
        self._llm_online = False

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._init_llm()
        return self._llm

    def _init_llm(self) -> None:
        profile = self.profile_repo.get()
        if profile:
            self._llm = get_client(
                backend=profile.get("llm_backend"),
                model=profile.get("llm_model"),
                base_url=profile.get("llm_base_url") or None,
            )
        else:
            self._llm = get_client()
        self._check_llm_status()

    def _check_llm_status(self) -> None:
        try:
            self._llm_online = self.llm.health_check()
        except Exception:
            self._llm_online = False

    def seed_problems(self) -> None:
        """Seed static problems on first run."""
        from codepractice.core.problem_bank import load_all_problems
        problems = load_all_problems()
        if problems:
            self.problem_repo.seed_if_empty(problems)

    # ── Screen management ──────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self.seed_problems()
        self._init_llm()
        # Update header LLM indicator
        header = self.query_one(AppHeader)
        header.llm_online = self._llm_online

    def compose(self) -> ComposeResult:
        yield AppHeader()
        with Horizontal():
            yield SidebarNav()
            with Container(id="content"):
                # Default screen content loaded via screen switching
                from codepractice.tui.screens.dashboard import DashboardContent
                yield DashboardContent()

    def action_goto(self, screen: str) -> None:
        self._switch_content(screen)

    def on_sidebar_nav_navigate(self, event: SidebarNav.Navigate) -> None:
        self._switch_content(event.screen)

    def _switch_content(self, screen_name: str) -> None:
        """Swap the content area with the requested screen's content."""
        sidebar = self.query_one(SidebarNav)
        sidebar.active_screen = screen_name

        content = self.query_one("#content", Container)
        content.remove_children()

        # Lazy import and mount the screen content
        widget = self._get_screen_content(screen_name)
        content.mount(widget)

    def _get_screen_content(self, name: str):
        """Factory: return the widget for a given screen name."""
        if name == "dashboard":
            from codepractice.tui.screens.dashboard import DashboardContent
            return DashboardContent()
        elif name == "practice":
            from codepractice.tui.screens.practice import PracticeContent
            return PracticeContent()
        elif name == "review":
            from codepractice.tui.screens.practice import PracticeContent
            return PracticeContent(review_mode=True)
        elif name == "python_track":
            from codepractice.tui.screens.python_track import PythonTrackContent
            return PythonTrackContent()
        elif name == "dsa_training":
            from codepractice.tui.screens.dsa_training import DSATrainingContent
            return DSATrainingContent()
        elif name == "resume_drill":
            from codepractice.tui.screens.resume_drill import ResumeDrillContent
            return ResumeDrillContent()
        elif name == "job_desc":
            from codepractice.tui.screens.job_desc import JobDescContent
            return JobDescContent()
        elif name == "learning_plan":
            from codepractice.tui.screens.learning_plan import LearningPlanContent
            return LearningPlanContent()
        elif name == "chat":
            from codepractice.tui.screens.chat import ChatContent
            return ChatContent()
        elif name == "progress":
            from codepractice.tui.screens.progress import ProgressContent
            return ProgressContent()
        elif name == "profile":
            from codepractice.tui.screens.profile import ProfileContent
            return ProfileContent()
        else:
            from codepractice.tui.screens.dashboard import DashboardContent
            return DashboardContent()


def run_app() -> None:
    """Entry point: launch the TUI."""
    app = CodePracticeApp()
    app.run()
