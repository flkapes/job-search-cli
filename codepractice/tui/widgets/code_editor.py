"""Multi-line code editor widget with Python syntax highlighting."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
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

    _language_id: str = "python"

    def compose(self) -> ComposeResult:
        yield Label("  ✎ solution.py — [dim]Ctrl+Enter to submit[/dim]", id="editor-header")
        yield TextArea(
            "",
            language="python",
            theme="monokai",
            show_line_numbers=True,
            id="code-input",
        )

    def set_language(self, language_id: str) -> None:
        """Switch syntax highlighting and the header filename to another language."""
        from codepractice.utils.languages import get_language

        spec = get_language(language_id)
        self._language_id = spec.id
        self.query_one("#editor-header", Label).update(
            f"  ✎ {spec.file_name} — [dim]Ctrl+Enter to submit[/dim]"
        )
        area = self.query_one("#code-input", TextArea)
        try:
            area.language = spec.editor_language
        except Exception:
            # Grammar not bundled — keep editing with no highlighting.
            try:
                area.language = None
            except Exception:
                pass

    @property
    def language(self) -> str:
        return self._language_id

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
