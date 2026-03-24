"""Creates and evolves adaptive learning plans via LLM."""

from __future__ import annotations

from typing import Generator

from codepractice.core.models import DayPlan, LearningPlan, PlanTask, UserProfile
from codepractice.llm.client import LLMClient, LLMError, extract_json
from codepractice.llm.prompts.plan_gen import (
    create_plan_prompt,
    daily_briefing_prompt,
    evolve_plan_prompt,
)


class LearningPlanManager:
    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def create_plan(
        self,
        goal: str,
        duration_days: int,
        profile: UserProfile | None = None,
        weak_areas: list[str] | None = None,
    ) -> LearningPlan | None:
        messages = create_plan_prompt(goal, duration_days, profile, weak_areas)
        try:
            raw = self.client.chat_sync(messages, temperature=0.7)
            return self._parse_plan(raw, goal, duration_days)
        except (LLMError, Exception):
            return self._default_plan(goal, duration_days)

    def evolve_plan(
        self,
        plan: LearningPlan,
        performance_summary: str,
        weak_areas: list[str],
    ) -> LearningPlan:
        days_remaining = plan.duration_days - plan.current_day + 1
        if days_remaining <= 0:
            return plan

        messages = evolve_plan_prompt(
            plan.title,
            plan.natural_language_goal,
            plan.current_day,
            days_remaining,
            performance_summary,
            weak_areas,
        )
        try:
            raw = self.client.chat_sync(messages, temperature=0.65)
            new_days_data = extract_json(raw)
            if isinstance(new_days_data, list):
                new_days = [self._parse_day(d) for d in new_days_data if isinstance(d, dict)]
                # Replace remaining days in schedule
                completed = [d for d in plan.daily_schedule if d.completed]
                plan.daily_schedule = completed + new_days
        except (LLMError, Exception):
            pass
        return plan

    def stream_daily_briefing(
        self, day: DayPlan, profile: UserProfile | None = None
    ) -> Generator[str, None, None]:
        messages = daily_briefing_prompt(day.theme, day.objectives, profile)
        try:
            yield from self.client.stream_chat(messages, temperature=0.9)
        except LLMError:
            yield f"Today's focus: {day.theme}. {', '.join(day.objectives[:2])}."

    # ── Parsing ────────────────────────────────────────────────────────────────

    def _parse_plan(self, raw: str, goal: str, duration_days: int) -> LearningPlan | None:
        data = extract_json(raw)
        if not isinstance(data, dict):
            return self._default_plan(goal, duration_days)

        schedule_data = data.get("daily_schedule", [])
        daily_schedule = [
            self._parse_day(d) for d in schedule_data if isinstance(d, dict)
        ]

        return LearningPlan(
            title=data.get("title", f"{duration_days}-Day Plan"),
            natural_language_goal=goal,
            duration_days=duration_days,
            daily_schedule=daily_schedule,
        )

    @staticmethod
    def _parse_day(data: dict) -> DayPlan:
        tasks = []
        for t in data.get("tasks", []):
            if isinstance(t, dict):
                tasks.append(
                    PlanTask(
                        type=t.get("type", "problem"),
                        title=t.get("title", ""),
                        description=t.get("description", ""),
                        problem_category=t.get("problem_category", "dsa"),
                        problem_subcategory=t.get("problem_subcategory", ""),
                        difficulty=t.get("difficulty", "medium"),
                        estimated_minutes=t.get("estimated_minutes", 15),
                    )
                )
        return DayPlan(
            day_number=int(data.get("day_number", 1)),
            theme=data.get("theme", "Practice"),
            objectives=data.get("objectives", []),
            tasks=tasks,
            estimated_minutes=int(data.get("estimated_minutes", 45)),
        )

    @staticmethod
    def _default_plan(goal: str, duration_days: int) -> LearningPlan:
        """Fallback plan when LLM is unavailable."""
        topics = [
            ("Python Fundamentals", "python_fundamentals"),
            ("Arrays & Hashing", "dsa"),
            ("Two Pointers", "dsa"),
            ("Sliding Window", "dsa"),
            ("Stacks & Queues", "dsa"),
            ("Binary Search", "dsa"),
            ("Trees", "dsa"),
            ("Graphs", "dsa"),
            ("Dynamic Programming", "dsa"),
            ("Review & Mock", "dsa"),
        ]
        days = []
        for i in range(1, duration_days + 1):
            theme, category = topics[(i - 1) % len(topics)]
            days.append(
                DayPlan(
                    day_number=i,
                    theme=theme,
                    objectives=[f"Practice {theme} concepts", "Solve 2-3 problems"],
                    tasks=[
                        PlanTask(
                            type="problem",
                            title=f"{theme} Practice",
                            problem_category=category,
                            difficulty="medium",
                            estimated_minutes=45,
                        )
                    ],
                    estimated_minutes=45,
                )
            )
        return LearningPlan(
            title=goal[:60] or f"{duration_days}-Day Coding Plan",
            natural_language_goal=goal,
            duration_days=duration_days,
            daily_schedule=days,
        )
