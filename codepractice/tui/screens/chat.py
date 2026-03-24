"""AI Coach chat — streaming conversation with full context."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Input, Label, Static

from codepractice.tui.widgets.streaming_output import StreamingOutput


class ChatMessage(Static):
    """A single chat message bubble."""

    DEFAULT_CSS = """
    ChatMessage {
        padding: 1 2;
        margin: 0 0 1 0;
        height: auto;
    }

    ChatMessage.user-msg {
        background: #1f6feb;
        color: #ffffff;
        margin-right: 12;
    }

    ChatMessage.assistant-msg {
        background: #1c2128;
        color: #c9d1d9;
        margin-left: 4;
    }
    """


class ChatContent(Widget):
    """Streaming AI coach chat interface."""

    DEFAULT_CSS = """
    ChatContent {
        height: 1fr;
        padding: 0 1;
    }

    ChatContent #chat-messages {
        height: 1fr;
        border: solid #30363d;
        background: #0d1117;
    }

    ChatContent #chat-input-bar {
        height: 3;
        dock: bottom;
        padding: 0 1;
        background: #161b22;
        border-top: solid #30363d;
    }

    ChatContent #chat-input {
        width: 1fr;
    }
    """

    BINDINGS = [
        Binding("escape", "clear_chat", "Clear", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Label("[bold #58a6ff]💬 AI Coach[/bold #58a6ff]")
        yield Static(
            "[#8b949e]Chat with your AI coding coach. Ask about concepts, "
            "get code reviewed, discuss your learning plan, or get motivation.[/#8b949e]"
        )

        with VerticalScroll(id="chat-messages"):
            yield Static(
                "[#8b949e]Start a conversation below. "
                "The coach knows your profile, plan, and progress.[/#8b949e]",
                id="chat-welcome",
            )

        yield StreamingOutput(id="chat-stream")

        with Vertical(id="chat-input-bar"):
            yield Input(
                placeholder="Ask anything... (Enter to send)",
                id="chat-input",
            )

    def on_mount(self) -> None:
        self._load_history()

    def _load_history(self) -> None:
        try:
            messages = self.app.chat_repo.get_history("default", limit=20)
            container = self.query_one("#chat-messages", VerticalScroll)
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                css_class = "user-msg" if role == "user" else "assistant-msg"
                prefix = "[bold]You:[/bold] " if role == "user" else "[bold]Coach:[/bold] "
                bubble = ChatMessage(f"{prefix}{content[:500]}", classes=css_class)
                container.mount(bubble)
            if messages:
                # Hide the welcome message
                self.query_one("#chat-welcome", Static).display = False
        except Exception:
            pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            text = event.value.strip()
            if text:
                event.input.value = ""
                self._send_message(text)

    def _send_message(self, text: str) -> None:
        # Show user message
        container = self.query_one("#chat-messages", VerticalScroll)
        self.query_one("#chat-welcome", Static).display = False
        container.mount(ChatMessage(f"[bold]You:[/bold] {text}", classes="user-msg"))

        # Stream AI response
        stream = self.query_one("#chat-stream", StreamingOutput)
        stream.clear()

        try:
            from codepractice.core.models import LearningPlan, UserProfile
            from codepractice.llm.services.chat_service import ChatService

            profile = None
            profile_data = self.app.profile_repo.get()
            if profile_data:
                profile = UserProfile.from_db(profile_data)

            active_plan = None
            plan_data = self.app.plan_repo.get_active()
            if plan_data:
                active_plan = LearningPlan(
                    title=plan_data["title"],
                    natural_language_goal=plan_data.get("natural_language_goal", ""),
                    current_day=plan_data.get("current_day", 1),
                    duration_days=plan_data.get("duration_days", 30),
                )

            stats = self.app.session_repo.get_stats()
            perf = f"Total solved: {stats['total_solved']}, Avg: {stats['avg_score']}%, Streak: {stats['active_days_30']}d"

            chat_service = ChatService(self.app.llm, self.app.chat_repo)
            full_response = stream.stream_sync(
                chat_service.stream_response(text, profile, active_plan, perf)
            )

            # Add response as a bubble too
            if full_response:
                container.mount(
                    ChatMessage(
                        f"[bold]Coach:[/bold] {full_response[:500]}",
                        classes="assistant-msg",
                    )
                )
                stream.clear()

        except Exception as e:
            stream.show_error(f"Chat error: {e}")

    def action_clear_chat(self) -> None:
        try:
            self.app.chat_repo.clear_conversation("default")
            container = self.query_one("#chat-messages", VerticalScroll)
            for child in list(container.children):
                if isinstance(child, ChatMessage):
                    child.remove()
            self.query_one("#chat-welcome", Static).display = True
        except Exception:
            pass
