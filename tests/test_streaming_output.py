"""Tests for the flicker-free streaming widget and token batching."""

from __future__ import annotations

from textual.app import App, ComposeResult

from codepractice.tui.widgets.streaming_output import StreamingOutput, TokenBatcher


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestTokenBatcher:
    def test_small_tokens_buffered(self):
        clock = FakeClock()
        b = TokenBatcher(max_chars=64, max_interval=0.05, clock=clock)
        assert b.add("a") is None
        assert b.add("b") is None

    def test_flush_on_newline(self):
        b = TokenBatcher(clock=FakeClock())
        b.add("hello")
        assert b.add(" world\n") == "hello world\n"

    def test_flush_on_size(self):
        b = TokenBatcher(max_chars=10, clock=FakeClock())
        b.add("12345")
        assert b.add("67890") == "1234567890"

    def test_flush_on_elapsed_time(self):
        clock = FakeClock()
        b = TokenBatcher(max_chars=1000, max_interval=0.05, clock=clock)
        assert b.add("a") is None
        clock.advance(0.06)
        assert b.add("b") == "ab"

    def test_flush_returns_none_when_empty(self):
        b = TokenBatcher(clock=FakeClock())
        assert b.flush() is None

    def test_flush_drains_buffer(self):
        b = TokenBatcher(clock=FakeClock())
        b.add("abc")
        assert b.flush() == "abc"
        assert b.flush() is None

    def test_no_tokens_lost_across_batches(self):
        clock = FakeClock()
        b = TokenBatcher(max_chars=8, clock=clock)
        tokens = ["ab", "cd", "ef", "gh", "ij\n", "kl"]
        out = []
        for t in tokens:
            batch = b.add(t)
            if batch:
                out.append(batch)
        tail = b.flush()
        if tail:
            out.append(tail)
        assert "".join(out) == "".join(tokens)


class StreamApp(App):
    def compose(self) -> ComposeResult:
        yield StreamingOutput(id="s")


class TestStreamingWidget:
    async def _wait_for(self, pilot, holder, key, tries=100):
        for _ in range(tries):
            await pilot.pause(0.05)
            if key in holder:
                return
        raise AssertionError(f"{key} never arrived")

    async def test_stream_in_worker_completes_with_full_text(self):
        result: dict = {}

        def gen():
            yield "hello "
            yield "world\n"
            yield "done"

        app = StreamApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingOutput)
            widget.stream_in_worker(gen(), on_complete=lambda t: result.update(text=t))
            await self._wait_for(pilot, result, "text")
        assert result["text"] == "hello world\ndone"

    async def test_stream_in_worker_reports_errors(self):
        result: dict = {}

        def gen():
            yield "partial "
            raise RuntimeError("backend died")

        app = StreamApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingOutput)
            widget.stream_in_worker(
                gen(),
                on_complete=lambda t: result.update(text=t),
                on_error=lambda e: result.update(error=str(e)),
            )
            await self._wait_for(pilot, result, "error")
        assert result["error"] == "backend died"
        assert "text" not in result

    async def test_stream_sync_returns_accumulated_text(self):
        app = StreamApp()
        async with app.run_test():
            widget = app.query_one(StreamingOutput)
            text = widget.stream_sync(iter(["a", "b", "c\n", "d"]))
        assert text == "abc\nd"

    async def test_update_replaces_content(self):
        app = StreamApp()
        async with app.run_test():
            widget = app.query_one(StreamingOutput)
            widget.write("old")
            widget.update("new content")
            assert widget.log.lines  # content present after replace

    async def test_new_stream_cancels_previous(self):
        """Streams share an exclusive worker group — only the latest completes."""
        import time as _time

        result: dict = {}

        def slow_gen():
            for i in range(50):
                _time.sleep(0.02)
                yield f"slow{i} "

        def fast_gen():
            yield "fast"

        app = StreamApp()
        async with app.run_test() as pilot:
            widget = app.query_one(StreamingOutput)
            widget.stream_in_worker(slow_gen(), on_complete=lambda t: result.update(slow=t))
            await pilot.pause(0.05)
            widget.stream_in_worker(fast_gen(), on_complete=lambda t: result.update(fast=t))
            await self._wait_for(pilot, result, "fast")
        assert result["fast"] == "fast"
        assert "slow" not in result
