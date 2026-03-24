"""Manages conversation context and streaming chat with the AI coach."""

from __future__ import annotations

from typing import Generator

from codepractice.core.models import LearningPlan, UserProfile
from codepractice.db.repositories.chat_history import ChatHistoryRepository
from codepractice.llm.client import LLMClient, LLMError
from codepractice.llm.prompts.chat import build_chat_system_prompt, build_resume_analysis_prompt


class ChatService:
    def __init__(
        self,
        client: LLMClient,
        chat_repo: ChatHistoryRepository,
        conversation_id: str = "default",
    ) -> None:
        self.client = client
        self.chat_repo = chat_repo
        self.conversation_id = conversation_id

    def stream_response(
        self,
        user_message: str,
        profile: UserProfile | None = None,
        active_plan: LearningPlan | None = None,
        recent_performance: str = "",
    ) -> Generator[str, None, None]:
        # Save user message
        self.chat_repo.add_message("user", user_message, self.conversation_id)

        # Build context-aware system prompt
        plan_summary = ""
        if active_plan and active_plan.today:
            plan_summary = (
                f"Active plan: {active_plan.title} (Day {active_plan.current_day}/{active_plan.duration_days})\n"
                f"Today's theme: {active_plan.today.theme}"
            )

        system = build_chat_system_prompt(profile, plan_summary, recent_performance)

        # Gather recent history
        history = self.chat_repo.get_messages_for_llm(self.conversation_id, limit=20)

        messages = [system] + history

        # Stream and accumulate for saving
        full_response = []
        try:
            for chunk in self.client.stream_chat(messages, temperature=0.8):
                full_response.append(chunk)
                yield chunk
        except LLMError as e:
            error_msg = f"\n\n*[LLM unavailable: {e}]*"
            full_response.append(error_msg)
            yield error_msg

        # Save assistant response
        if full_response:
            self.chat_repo.add_message(
                "assistant", "".join(full_response), self.conversation_id
            )

    def analyze_resume(self, resume_text: str) -> dict:
        """Parse resume via LLM and return structured data."""
        from codepractice.llm.client import extract_json
        messages = build_resume_analysis_prompt(resume_text)
        try:
            raw = self.client.chat_sync(messages, temperature=0.2)
            data = extract_json(raw)
            if isinstance(data, dict):
                return data
        except (LLMError, Exception):
            pass
        return {}

    def get_history(self, limit: int = 50) -> list[dict]:
        return self.chat_repo.get_history(self.conversation_id, limit)

    def clear(self) -> None:
        self.chat_repo.clear_conversation(self.conversation_id)
