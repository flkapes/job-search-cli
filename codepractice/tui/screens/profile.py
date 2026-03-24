"""Profile & settings screen — user profile, LLM backend config."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static

from codepractice.tui.widgets.streaming_output import StreamingOutput


class ProfileContent(Widget):
    """User profile and LLM settings."""

    DEFAULT_CSS = """
    ProfileContent {
        height: 1fr;
        padding: 0 1;
    }

    ProfileContent .settings-section {
        background: #161b22;
        border: solid #30363d;
        padding: 1 2;
        margin: 1 0;
    }

    ProfileContent .field-label {
        color: #8b949e;
        margin: 1 0 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label("[bold #58a6ff]👤 Profile & Settings[/bold #58a6ff]\n")

            # Profile section
            with Vertical(classes="settings-section"):
                yield Label("[bold]Profile[/bold]")
                yield Label("Name", classes="field-label")
                yield Input(placeholder="Your name", id="profile-name")
                yield Label("Target Role", classes="field-label")
                yield Input(placeholder="e.g., Backend Python Engineer", id="profile-role")
                yield Label("Experience Level", classes="field-label")
                yield Select(
                    [("Junior", "junior"), ("Mid-Level", "mid"), ("Senior", "senior")],
                    value="mid",
                    id="profile-level",
                )

            # LLM section
            with Vertical(classes="settings-section"):
                yield Label("[bold]LLM Configuration[/bold]")
                yield Label("Backend", classes="field-label")
                yield Select(
                    [("Ollama", "ollama"), ("LM Studio", "lmstudio")],
                    value="ollama",
                    id="llm-backend",
                )
                yield Label("Model", classes="field-label")
                yield Input(placeholder="e.g., llama3, codellama, deepseek-coder", id="llm-model")
                yield Label("Base URL", classes="field-label")
                yield Input(placeholder="e.g., http://localhost:11434", id="llm-url")

                with Horizontal():
                    yield Button("🔍 Test Connection", id="btn-test-llm", classes="secondary-btn")
                    yield Button("📋 List Models", id="btn-list-models", classes="secondary-btn")
                yield StreamingOutput(id="llm-test-output")

            # Actions
            with Horizontal():
                yield Button("💾 Save Settings", id="btn-save-profile", classes="primary-btn")
                yield Button("📤 Export Data", id="btn-export", classes="secondary-btn")

            yield Static("", id="save-status")

    def on_mount(self) -> None:
        self._load_profile()

    def _load_profile(self) -> None:
        try:
            profile = self.app.profile_repo.get()
            if profile:
                if profile.get("name"):
                    self.query_one("#profile-name", Input).value = profile["name"]
                if profile.get("target_role"):
                    self.query_one("#profile-role", Input).value = profile["target_role"]
                if profile.get("experience_level"):
                    self.query_one("#profile-level", Select).value = profile["experience_level"]
                if profile.get("llm_backend"):
                    self.query_one("#llm-backend", Select).value = profile["llm_backend"]
                if profile.get("llm_model"):
                    self.query_one("#llm-model", Input).value = profile["llm_model"]
                if profile.get("llm_base_url"):
                    self.query_one("#llm-url", Input).value = profile["llm_base_url"]
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-profile":
            self._save_profile()
        elif event.button.id == "btn-test-llm":
            self._test_llm()
        elif event.button.id == "btn-list-models":
            self._list_models()
        elif event.button.id == "btn-export":
            self._export_data()

    def _save_profile(self) -> None:
        data = {
            "name": self.query_one("#profile-name", Input).value,
            "target_role": self.query_one("#profile-role", Input).value,
            "experience_level": str(self.query_one("#profile-level", Select).value),
            "llm_backend": str(self.query_one("#llm-backend", Select).value),
            "llm_model": self.query_one("#llm-model", Input).value,
            "llm_base_url": self.query_one("#llm-url", Input).value,
        }
        try:
            if self.app.profile_repo.exists():
                self.app.profile_repo.update(data)
            else:
                self.app.profile_repo.create(data)
            # Reinitialize LLM client with new settings
            self.app._llm = None
            self.app._init_llm()
            self.query_one("#save-status", Static).update("[green]✓ Settings saved![/green]")
        except Exception as e:
            self.query_one("#save-status", Static).update(f"[red]✗ Error: {e}[/red]")

    def _test_llm(self) -> None:
        stream = self.query_one("#llm-test-output", StreamingOutput)
        stream.clear()
        stream.show_info("Testing LLM connection...")
        try:
            if self.app.llm.health_check():
                stream.show_success("Connected successfully!")
                # Quick test message
                response = self.app.llm.chat_sync(
                    [{"role": "user", "content": "Say 'Hello!' in one word."}],
                    temperature=0.1,
                )
                stream.write_line(f"  Response: {response[:100]}")
            else:
                stream.show_error("Could not connect to LLM backend.")
        except Exception as e:
            stream.show_error(f"Connection failed: {e}")

    def _list_models(self) -> None:
        stream = self.query_one("#llm-test-output", StreamingOutput)
        stream.clear()
        try:
            models = self.app.llm.list_models()
            if models:
                stream.show_success(f"Found {len(models)} models:")
                for m in models:
                    stream.write_line(f"  • {m}")
            else:
                stream.show_info("No models found or backend unavailable.")
        except Exception as e:
            stream.show_error(f"Error: {e}")

    def _export_data(self) -> None:
        try:
            from codepractice.db.export import export_all
            path = export_all(self.app._db)
            self.query_one("#save-status", Static).update(
                f"[green]✓ Exported to: {path}[/green]"
            )
        except Exception as e:
            self.query_one("#save-status", Static).update(f"[red]✗ Export failed: {e}[/red]")
