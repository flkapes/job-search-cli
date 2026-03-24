"""Real-time LLM token streaming display widget."""

from __future__ import annotations

from typing import Generator

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog


class StreamingOutput(Widget):
    """Displays text that streams in token-by-token from an LLM response."""

    DEFAULT_CSS = """
    StreamingOutput {
        height: auto;
        min-height: 4;
        max-height: 40;
    }

    StreamingOutput RichLog {
        background: #161b22;
        border: solid #30363d;
        padding: 1 2;
        scrollbar-size: 1 1;
        overflow-y: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
            id="stream-log",
        )

    @property
    def log(self) -> RichLog:
        return self.query_one("#stream-log", RichLog)

    def clear(self) -> None:
        self.log.clear()

    def write(self, text: str) -> None:
        self.log.write(text)

    def write_line(self, text: str = "") -> None:
        self.log.write(text + "\n")

    def stream_sync(self, generator: Generator[str, None, None]) -> str:
        """Consume a synchronous token generator and display output.

        Returns the accumulated full text.
        """
        accumulated = []
        buffer = ""
        for chunk in generator:
            buffer += chunk
            accumulated.append(chunk)
            # Write in small bursts for smooth display
            if "\n" in buffer or len(buffer) > 60:
                self.log.write(buffer)
                buffer = ""
        if buffer:
            self.log.write(buffer)
        return "".join(accumulated)

    def show_error(self, message: str) -> None:
        self.log.write(f"[red]✗ {message}[/red]\n")

    def show_success(self, message: str) -> None:
        self.log.write(f"[green]✓ {message}[/green]\n")

    def show_info(self, message: str) -> None:
        self.log.write(f"[#8b949e]{message}[/#8b949e]\n")
