"""Navigation sidebar with screen buttons."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, Static


class SidebarNav(Widget):
    """Left sidebar with navigation buttons."""

    DEFAULT_CSS = """
    SidebarNav {
        dock: left;
        width: 26;
        background: #161b22;
        border-right: solid #30363d;
        padding: 1 0;
    }

    SidebarNav .section-title {
        color: #484f58;
        text-style: italic;
        padding: 1 2 0 2;
        margin-top: 1;
    }

    SidebarNav .nav-btn {
        width: 100%;
        height: 3;
        background: transparent;
        color: #c9d1d9;
        border: none;
        content-align: left middle;
        padding: 0 2;
        margin: 0;
        text-style: none;
    }

    SidebarNav .nav-btn:hover {
        background: #1c2128;
        color: #58a6ff;
    }

    SidebarNav .nav-btn.-active {
        background: #1f6feb;
        color: #ffffff;
        text-style: bold;
    }

    SidebarNav #stats-mini {
        margin-top: 1;
        padding: 1 2;
        color: #8b949e;
    }
    """

    active_screen: reactive[str] = reactive("dashboard")

    class Navigate(Message):
        """Emitted when user clicks a nav item."""
        def __init__(self, screen: str) -> None:
            self.screen = screen
            super().__init__()

    NAV_ITEMS = [
        ("practice", [
            ("dashboard", "🏠 Dashboard"),
            ("python_track", "🐍 Python Track"),
            ("dsa_training", "🧩 DSA Patterns"),
            ("practice", "⚡ Free Practice"),
        ]),
        ("prepare", [
            ("resume_drill", "📄 Resume Drill"),
            ("job_desc", "💼 Job Description"),
            ("learning_plan", "📅 Learning Plan"),
        ]),
        ("tools", [
            ("chat", "💬 AI Coach"),
            ("progress", "📊 Progress"),
            ("profile", "👤 Profile"),
        ]),
    ]

    def compose(self) -> ComposeResult:
        for section_name, items in self.NAV_ITEMS:
            yield Label(f"  {section_name.upper()}", classes="section-title")
            for screen_id, label in items:
                yield Button(label, id=f"nav-{screen_id}", classes="nav-btn")
        yield Static("", id="stats-mini")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("nav-"):
            screen = btn_id.removeprefix("nav-")
            self.post_message(self.Navigate(screen))

    def watch_active_screen(self, screen_name: str) -> None:
        for btn in self.query(".nav-btn"):
            btn_screen = (btn.id or "").removeprefix("nav-")
            if btn_screen == screen_name:
                btn.add_class("-active")
            else:
                btn.remove_class("-active")

    def update_stats(self, today: int = 0, streak: int = 0) -> None:
        mini = self.query_one("#stats-mini", Static)
        mini.update(f"  Today: {today} solved\n  Streak: {streak} days")
