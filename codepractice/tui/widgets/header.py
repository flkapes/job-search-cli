"""Global navigation header with keyboard shortcuts."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static


class AppHeader(Widget):
    """Top navigation bar showing app name and keyboard shortcuts."""

    DEFAULT_CSS = """
    AppHeader {
        dock: top;
        height: 3;
        background: #161b22;
        border-bottom: solid #30363d;
        padding: 0 1;
    }

    AppHeader #header-inner {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    AppHeader .app-title {
        color: #58a6ff;
        text-style: bold;
        width: auto;
        margin: 0 2 0 0;
    }

    AppHeader .nav-shortcut {
        color: #484f58;
        width: auto;
        margin: 0 1;
    }

    AppHeader .nav-shortcut .key {
        color: #8b949e;
        text-style: bold;
    }

    AppHeader .llm-status {
        dock: right;
        width: auto;
        margin: 0 1;
    }
    """

    llm_online: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        with Horizontal(id="header-inner"):
            yield Label("⬡ CodePractice", classes="app-title")
            yield Label("[d]ashboard", classes="nav-shortcut")
            yield Label("[p]ractice", classes="nav-shortcut")
            yield Label("[t]rack", classes="nav-shortcut")
            yield Label("[l]earn", classes="nav-shortcut")
            yield Label("[c]hat", classes="nav-shortcut")
            yield Label("⚙ [s]ettings", classes="nav-shortcut")
            yield Label("● LLM", id="llm-indicator", classes="llm-status")

    def watch_llm_online(self, online: bool) -> None:
        indicator = self.query_one("#llm-indicator", Label)
        if online:
            indicator.update("[green]● LLM[/green]")
        else:
            indicator.update("[red]○ LLM[/red]")
