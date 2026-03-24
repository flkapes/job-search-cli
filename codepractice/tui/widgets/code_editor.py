"""Multi-line code editor widget with Python syntax highlighting."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, TextArea


class CodeEditor(Widget):
    """Code input widget wrapping Textual's TextArea with Python highlighting."""

    DEFAULT_CSS = """
    CodeEditor {
        height: 1fr;
        min-height: 10;
    }

    CodeEditor #editor-header {
        height: 1;
        background: #1c2128;
        color: #8b949e;
        padding: 0 2;
    }

    CodeEditor TextArea {
        height: 1fr;
        background: #0d1117;
        border: solid #30363d;
    }

    CodeEditor TextArea:focus {
        border: solid #58a6ff;
    }
    """

    BINDINGS = [
        Binding("ctrl+enter", "submit_code", "Submit", show=True, priority=True),
    ]

    class CodeSubmitted(Message):
        """Fired when user presses Ctrl+Enter."""
        def __init__(self, code: str) -> None:
            self.code = code
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Label("  ✎ solution.py — [dim]Ctrl+Enter to submit[/dim]", id="editor-header")
        yield TextArea(
            "",
            language="python",
            theme="monokai",
            show_line_numbers=True,
            id="code-input",
        )

    def get_code(self) -> str:
        return self.query_one("#code-input", TextArea).text

    def set_code(self, code: str) -> None:
        self.query_one("#code-input", TextArea).text = code

    def clear(self) -> None:
        self.query_one("#code-input", TextArea).text = ""

    def action_submit_code(self) -> None:
        code = self.get_code()
        if code.strip():
            self.post_message(self.CodeSubmitted(code))
