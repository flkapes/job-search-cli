"""Pydantic data models — the contracts between every layer."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# ── Enums ──────────────────────────────────────────────────────────────────────

class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class ProblemCategory(str, Enum):
    python_fundamentals = "python_fundamentals"
    dsa = "dsa"
    practical = "practical"
    system_design = "system_design"


class ProblemSource(str, Enum):
    static = "static"
    ai_generated = "ai_generated"
    jd_driven = "jd_driven"
    resume_driven = "resume_driven"


class SessionType(str, Enum):
    free = "free"
    plan = "plan"
    dsa = "dsa"
    python = "python"
    jd = "jd"
    resume = "resume"
    chat = "chat"


class PlanStatus(str, Enum):
    active = "active"
    paused = "paused"
    completed = "completed"


class ExperienceLevel(str, Enum):
    junior = "junior"
    mid = "mid"
    senior = "senior"


class LLMBackend(str, Enum):
    ollama = "ollama"
    lmstudio = "lmstudio"


# ── Problem Models ─────────────────────────────────────────────────────────────

class Example(BaseModel):
    input: str = ""
    output: str = ""
    explanation: str = ""


class Solution(BaseModel):
    code: str = ""
    explanation: str = ""
    time_complexity: str = "O(?)"
    space_complexity: str = "O(?)"


class Problem(BaseModel):
    id: int | None = None
    source: ProblemSource = ProblemSource.static
    category: str = "dsa"
    subcategory: str = ""
    difficulty: Difficulty = Difficulty.medium
    title: str
    description: str
    constraints: str = ""
    examples: list[Example] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    solution: Solution | None = None
    tags: list[str] = Field(default_factory=list)
    times_shown: int = 0
    times_solved: int = 0

    @classmethod
    def from_db(cls, row: dict) -> "Problem":
        """Construct from a database row dict."""
        examples_raw = row.get("examples", [])
        examples = []
        for e in (examples_raw if isinstance(examples_raw, list) else []):
            if isinstance(e, dict):
                examples.append(Example(**e))
            elif isinstance(e, Example):
                examples.append(e)

        solution_raw = row.get("solution")
        solution = None
        if solution_raw and isinstance(solution_raw, dict):
            solution = Solution(**solution_raw)
        elif isinstance(solution_raw, Solution):
            solution = solution_raw

        return cls(
            id=row.get("id"),
            source=row.get("source", "static"),
            category=row.get("category", "dsa"),
            subcategory=row.get("subcategory", ""),
            difficulty=row.get("difficulty", "medium"),
            title=row["title"],
            description=row["description"],
            constraints=row.get("constraints", ""),
            examples=examples,
            hints=row.get("hints", []),
            solution=solution,
            tags=row.get("tags", []),
            times_shown=row.get("times_shown", 0),
            times_solved=row.get("times_solved", 0),
        )

    def to_db(self) -> dict:
        return {
            "source": self.source.value,
            "category": self.category,
            "subcategory": self.subcategory,
            "difficulty": self.difficulty.value,
            "title": self.title,
            "description": self.description,
            "constraints": self.constraints,
            "examples": [e.model_dump() for e in self.examples],
            "hints": self.hints,
            "solution": self.solution.model_dump() if self.solution else None,
            "tags": self.tags,
        }


# ── Feedback Models ────────────────────────────────────────────────────────────

class AIFeedback(BaseModel):
    correctness_score: float = 0.0   # 0-1
    efficiency_score: float = 0.0    # 0-1
    style_score: float = 0.0         # 0-1
    overall_score: float = 0.0       # 0-1 composite
    verdict: Literal["correct", "partial", "incorrect"] = "incorrect"
    explanation: str = ""
    improvements: list[str] = Field(default_factory=list)
    optimized_solution: str | None = None
    passed: bool = False

    @classmethod
    def from_score(cls, score: float, explanation: str = "", **kwargs) -> "AIFeedback":
        passed = score >= 0.7
        verdict = "correct" if score >= 0.85 else "partial" if score >= 0.5 else "incorrect"
        return cls(
            overall_score=score,
            correctness_score=score,
            efficiency_score=kwargs.get("efficiency_score", score * 0.9),
            style_score=kwargs.get("style_score", score * 0.85),
            verdict=verdict,
            explanation=explanation,
            passed=passed,
        )


class TestResult(BaseModel):
    passed: bool
    stdout: str = ""
    stderr: str = ""
    error: str = ""
    runtime_ms: float = 0.0


# ── Session Models ─────────────────────────────────────────────────────────────

class ProblemAttempt(BaseModel):
    id: int | None = None
    session_id: int
    problem_id: int
    user_code: str = ""
    user_explanation: str = ""
    ai_feedback: AIFeedback | None = None
    time_spent_sec: int = 0
    hints_used: int = 0
    passed: bool = False
    attempted_at: datetime = Field(default_factory=datetime.now)


class PracticeSession(BaseModel):
    id: int | None = None
    session_type: SessionType = SessionType.free
    plan_id: int | None = None
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: datetime | None = None
    attempts: list[ProblemAttempt] = Field(default_factory=list)

    @property
    def solved_count(self) -> int:
        return sum(1 for a in self.attempts if a.passed)

    @property
    def avg_score(self) -> float:
        scores = [a.ai_feedback.overall_score for a in self.attempts if a.ai_feedback]
        return sum(scores) / len(scores) if scores else 0.0


# ── Learning Plan Models ───────────────────────────────────────────────────────

class PlanTask(BaseModel):
    type: Literal["problem", "reading", "review", "quiz"] = "problem"
    title: str = ""
    description: str = ""
    problem_id: int | None = None
    problem_category: str = ""
    problem_subcategory: str = ""
    difficulty: str = "medium"
    estimated_minutes: int = 15


class DayPlan(BaseModel):
    day_number: int
    theme: str = ""
    objectives: list[str] = Field(default_factory=list)
    tasks: list[PlanTask] = Field(default_factory=list)
    estimated_minutes: int = 45
    completed: bool = False


class LearningPlan(BaseModel):
    id: int | None = None
    title: str
    natural_language_goal: str = ""
    duration_days: int = 30
    current_day: int = 1
    status: PlanStatus = PlanStatus.active
    daily_schedule: list[DayPlan] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def progress_pct(self) -> float:
        if not self.daily_schedule:
            return 0.0
        completed = sum(1 for d in self.daily_schedule if d.completed)
        return completed / len(self.daily_schedule)

    @property
    def today(self) -> DayPlan | None:
        for d in self.daily_schedule:
            if d.day_number == self.current_day:
                return d
        return None


# ── Profile Models ─────────────────────────────────────────────────────────────

class ResumeProject(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class ResumeParsed(BaseModel):
    skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    years_experience: int = 0
    summary: str = ""


class UserProfile(BaseModel):
    name: str = ""
    resume_text: str = ""
    resume_parsed: ResumeParsed = Field(default_factory=ResumeParsed)
    target_role: str = ""
    experience_level: ExperienceLevel = ExperienceLevel.mid
    llm_backend: LLMBackend = LLMBackend.ollama
    llm_model: str = "llama3"
    llm_base_url: str = ""

    @classmethod
    def from_db(cls, row: dict) -> "UserProfile":
        parsed_raw = row.get("resume_parsed", {})
        parsed = ResumeParsed(**parsed_raw) if isinstance(parsed_raw, dict) else ResumeParsed()
        return cls(
            name=row.get("name", ""),
            resume_text=row.get("resume_text", ""),
            resume_parsed=parsed,
            target_role=row.get("target_role", ""),
            experience_level=row.get("experience_level", "mid"),
            llm_backend=row.get("llm_backend", "ollama"),
            llm_model=row.get("llm_model", "llama3"),
            llm_base_url=row.get("llm_base_url", ""),
        )


# ── Stats Models ───────────────────────────────────────────────────────────────

class AppStats(BaseModel):
    total_attempts: int = 0
    total_solved: int = 0
    avg_score: float = 0.0
    today_solved: int = 0
    active_days_30: int = 0
    current_streak: int = 0
    active_plan: str | None = None

    @property
    def solve_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.total_solved / self.total_attempts
