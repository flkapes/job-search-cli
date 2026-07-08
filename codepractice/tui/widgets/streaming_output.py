"""Real-time LLM token streaming display widget.

Rendering approach modeled on Claude Code's fullscreen renderer:

- Textual already draws on the alternate screen buffer and wraps frames in
  synchronized-output mode (DEC 2026) where the terminal supports it, so the
  terminal only repaints complete frames.
- What this widget adds is the app-level half: tokens are consumed on a
  background worker thread (the UI thread never blocks on the LLM), writes
  are coalesced into frame-sized batches instead of per-token updates, and
  auto-follow pauses when the user scrolls up and resumes at the bottom.
"""

from __future__ import annotations

import time
from typing import Callable, Generator

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog


class TokenBatcher:
    """Coalesces streamed tokens into frame-sized flushes.

    Emitting one write per token forces a relayout per token; batching by
    size, newline, or elapsed time yields a few complete frames per second
    instead, which the terminal can paint atomically.
    """

    def __init__(
        self,
        max_chars: int = 64,
        max_interval: float = 0.05,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_chars = max_chars
        self.max_interval = max_interval
        self._clock = clock
        self._parts: list[str] = []
        self._chars = 0
        self._last_flush = clock()

    def add(self, token: str) -> str | None:
        """Buffer a token. Returns text to display when a flush is due."""
        self._parts.append(token)
        self._chars += len(token)
        if (
            "\n" in token
            or self._chars >= self.max_chars
            or self._clock() - self._last_flush >= self.max_interval
        ):
            return self.flush()
        return None

    def flush(self) -> str | None:
        """Return and clear any buffered text."""
        self._last_flush = self._clock()
        if not self._parts:
            return None
        text = "".join(self._parts)
        self._parts.clear()
        self._chars = 0
        return text


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

    def update(self, text: str) -> None:
        """Replace the current content with the given text."""
        log = self.log
        log.clear()
        log.write(text)

    # ── Streaming ──────────────────────────────────────────────────────────────

    def _append(self, text: str) -> None:
        """Write a batch with auto-follow: stay pinned to the bottom only if
        the user hasn't scrolled up (Claude Code's auto-follow behavior)."""
        log = self.log
        follow = bool(getattr(log, "is_vertical_scroll_end", True))
        log.write(text, scroll_end=follow)

    def stream_in_worker(
        self,
        generator: Generator[str, None, None],
        on_complete: Callable[[str], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Consume a token generator on a background thread.

        The UI thread never blocks: batched writes (and the completion or
        error callback, called with the accumulated text) are marshaled back
        with ``call_from_thread``, so the app keeps painting complete frames
        and the input stays responsive while tokens arrive. Starting a new
        stream cancels the previous one.
        """
        app = self.app

        def _consume() -> None:
            from textual.worker import get_current_worker

            worker = get_current_worker()
            batcher = TokenBatcher()
            accumulated: list[str] = []
            try:
                for token in generator:
                    if worker.is_cancelled:
                        return
                    accumulated.append(token)
                    batch = batcher.add(token)
                    if batch:
                        app.call_from_thread(self._append, batch)
                tail = batcher.flush()
                if tail and not worker.is_cancelled:
                    app.call_from_thread(self._append, tail)
            except Exception as e:
                if on_error and not worker.is_cancelled:
                    app.call_from_thread(on_error, e)
                return
            if on_complete and not worker.is_cancelled:
                app.call_from_thread(on_complete, "".join(accumulated))

        self.run_worker(_consume, thread=True, exclusive=True, group="llm-stream")

    def stream_sync(self, generator: Generator[str, None, None]) -> str:
        """Blocking variant kept for callers that already run off the UI thread.

        Returns the accumulated full text.
        """
        accumulated = []
        batcher = TokenBatcher()
        for token in generator:
            accumulated.append(token)
            batch = batcher.add(token)
            if batch:
                self.log.write(batch)
        tail = batcher.flush()
        if tail:
            self.log.write(tail)
        return "".join(accumulated)

    # ── Status helpers ─────────────────────────────────────────────────────────

    def show_error(self, message: str) -> None:
        self.log.write(f"[red]✗ {message}[/red]\n")

    def show_success(self, message: str) -> None:
        self.log.write(f"[green]✓ {message}[/green]\n")

    def show_info(self, message: str) -> None:
        self.log.write(f"[#8b949e]{message}[/#8b949e]\n")
