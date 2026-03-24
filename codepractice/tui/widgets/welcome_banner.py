"""Animated ASCII art welcome banner."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


BANNER_ART = r"""[bold #58a6ff]
   ██████╗ ██████╗ ██████╗ ███████╗
  ██╔════╝██╔═══██╗██╔══██╗██╔════╝
  ██║     ██║   ██║██║  ██║█████╗
  ██║     ██║   ██║██║  ██║██╔══╝
  ╚██████╗╚██████╔╝██████╔╝███████╗
   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
  [bold #bc8cff]P R A C T I C E[/bold #bc8cff]
[/bold #58a6ff]
[#8b949e]  AI-Powered Coding Practice Platform
  Master Python · Crush DSA · Land the Job[/#8b949e]
"""


class WelcomeBanner(Widget):
    """ASCII art welcome banner for the dashboard."""

    DEFAULT_CSS = """
    WelcomeBanner {
        height: auto;
        content-align: center middle;
        padding: 0 0 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(BANNER_ART, id="banner-text")
