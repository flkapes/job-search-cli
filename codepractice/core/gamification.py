"""Gamification engine: XP accrual rules, levels, and achievement definitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# ── XP rules ───────────────────────────────────────────────────────────────────

XP_BASE = {"easy": 10, "medium": 20, "hard": 35}
XP_SPEED_BONUS = 5          # solved in under 5 minutes
XP_NO_HINTS_BONUS = 5       # solved without peeking at hints
SPEED_BONUS_THRESHOLD_SEC = 300


def xp_for_attempt(
    difficulty: str,
    score: float,
    passed: bool,
    time_spent_sec: int = 0,
    hints_used: int = 0,
) -> int:
    """XP earned for one attempt: base by difficulty × score, bonuses on pass."""
    base = XP_BASE.get(difficulty, XP_BASE["medium"])
    score = max(0.0, min(1.0, score))
    xp = base * score
    if not passed:
        # Failed attempts still teach something, but earn a fraction.
        return int(round(xp * 0.25))
    if 0 < time_spent_sec < SPEED_BONUS_THRESHOLD_SEC:
        xp += XP_SPEED_BONUS
    if hints_used == 0:
        xp += XP_NO_HINTS_BONUS
    return int(round(xp))


# ── Levels ─────────────────────────────────────────────────────────────────────

LEVELS: list[tuple[int, str]] = [
    (0, "Intern"),
    (100, "Junior Engineer"),
    (300, "Engineer"),
    (600, "Senior Engineer"),
    (1000, "Staff Engineer"),
    (1800, "Senior Staff Engineer"),
    (3000, "Principal Engineer"),
    (5000, "Distinguished Engineer"),
]


@dataclass
class LevelInfo:
    level: int              # 1-based
    title: str
    xp: int
    current_threshold: int
    next_threshold: int | None

    @property
    def progress_to_next(self) -> float:
        if self.next_threshold is None:
            return 1.0
        span = self.next_threshold - self.current_threshold
        return (self.xp - self.current_threshold) / span if span else 1.0


def level_for_xp(total_xp: int) -> LevelInfo:
    total_xp = max(0, total_xp)
    level_idx = 0
    for i, (threshold, _) in enumerate(LEVELS):
        if total_xp >= threshold:
            level_idx = i
    threshold, title = LEVELS[level_idx]
    next_threshold = LEVELS[level_idx + 1][0] if level_idx + 1 < len(LEVELS) else None
    return LevelInfo(
        level=level_idx + 1,
        title=title,
        xp=total_xp,
        current_threshold=threshold,
        next_threshold=next_threshold,
    )


# ── Achievements ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Achievement:
    key: str
    name: str
    description: str
    icon: str


ACHIEVEMENTS: list[Achievement] = [
    Achievement("first_solve", "First Solve", "Solve your first problem", "🌱"),
    Achievement("ten_solved", "Getting Warm", "Solve 10 problems", "🔥"),
    Achievement("fifty_solved", "Half Century", "Solve 50 problems", "💪"),
    Achievement("hundred_solved", "Centurion", "Solve 100 problems", "🏛"),
    Achievement("seven_day_streak", "7-Day Streak", "Practice 7 days in a row", "📅"),
    Achievement("thirty_day_month", "Iron Month", "Practice on 30 days within a month", "🗓"),
    Achievement("perfect_score", "Perfect Score", "Score 100% on a problem", "💯"),
    Achievement("speed_demon", "Speed Demon", "Solve a problem in under 5 minutes", "⚡"),
    Achievement("no_hints_ten", "Self-Reliant", "Solve 10 problems without hints", "🧭"),
    Achievement("dsa_master", "DSA Master", "Solve a problem in all 10 DSA patterns", "🧩"),
    Achievement("pythonista", "Pythonista", "Solve 25 Python fundamentals problems", "🐍"),
    Achievement("plan_finisher", "Plan Finisher", "Complete a learning plan", "🎓"),
    Achievement("simulation_pass", "Interview Ready", "Pass an interview simulation", "🧪"),
    Achievement("comeback", "Comeback Kid", "Solve a problem you previously failed", "🔄"),
    Achievement("level_staff", "Staff Engineer", "Reach the Staff Engineer level", "🌟"),
    Achievement("librarian", "Librarian", "Bookmark 5 problems", "📚"),
    Achievement("problem_author", "Problem Author", "Create a custom problem", "✏️"),
    Achievement("polyglot", "Polyglot", "Solve problems in 2+ languages", "🌍"),
]

ACHIEVEMENTS_BY_KEY = {a.key: a for a in ACHIEVEMENTS}
DSA_PATTERN_COUNT = 10


def current_streak_days(active_days: list[str], today: date | None = None) -> int:
    """Consecutive practice days ending today or yesterday.

    ``active_days`` are ISO date strings (from daily activity rows).
    A streak survives if the last practice day was yesterday.
    """
    if not active_days:
        return 0
    today = today or date.today()
    days = set()
    for d in active_days:
        try:
            days.add(date.fromisoformat(str(d)[:10]))
        except ValueError:
            continue
    if not days:
        return 0

    cursor = today if today in days else today - timedelta(days=1)
    if cursor not in days:
        return 0
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def check_achievements(context: dict, already_unlocked: set[str]) -> list[Achievement]:
    """Return newly earned achievements given a stats context.

    Expected context keys (all optional, default falsy):
      total_solved, streak_days, active_days_30, last_score, last_passed,
      last_time_spent_sec, last_hints_used, no_hint_solves, dsa_patterns_solved,
      python_solved, plan_completed, simulation_passed, solved_after_fail,
      total_xp, bookmark_count, custom_problem_count, languages_solved
    """
    def ctx(key, default=0):
        return context.get(key, default)

    checks: dict[str, bool] = {
        "first_solve": ctx("total_solved") >= 1,
        "ten_solved": ctx("total_solved") >= 10,
        "fifty_solved": ctx("total_solved") >= 50,
        "hundred_solved": ctx("total_solved") >= 100,
        "seven_day_streak": ctx("streak_days") >= 7,
        "thirty_day_month": ctx("active_days_30") >= 30,
        "perfect_score": bool(ctx("last_passed")) and ctx("last_score", 0.0) >= 1.0,
        "speed_demon": bool(ctx("last_passed")) and 0 < ctx("last_time_spent_sec") < SPEED_BONUS_THRESHOLD_SEC,
        "no_hints_ten": ctx("no_hint_solves") >= 10,
        "dsa_master": ctx("dsa_patterns_solved") >= DSA_PATTERN_COUNT,
        "pythonista": ctx("python_solved") >= 25,
        "plan_finisher": bool(ctx("plan_completed")),
        "simulation_pass": bool(ctx("simulation_passed")),
        "comeback": bool(ctx("solved_after_fail")),
        "level_staff": level_for_xp(ctx("total_xp")).title in (
            "Staff Engineer", "Senior Staff Engineer", "Principal Engineer", "Distinguished Engineer"
        ),
        "librarian": ctx("bookmark_count") >= 5,
        "problem_author": ctx("custom_problem_count") >= 1,
        "polyglot": ctx("languages_solved") >= 2,
    }

    return [
        ACHIEVEMENTS_BY_KEY[key]
        for key, earned in checks.items()
        if earned and key not in already_unlocked
    ]


def award_attempt(
    gam_repo,
    session_repo,
    problem,
    attempt_id: int | None,
    score: float,
    passed: bool,
    time_spent_sec: int = 0,
    hints_used: int = 0,
) -> tuple[int, list[Achievement]]:
    """Record XP for an attempt and unlock any newly earned achievements.

    Returns (xp_earned, newly_unlocked). Individual context queries are
    best-effort — a failure in one must not block the reward flow.

    Anti-farming: the full reward is paid on a problem's first solve. Solving
    it again pays 25%, and failing a problem you have already solved pays
    nothing, so resubmitting the same problem cannot grind XP.
    """
    difficulty = getattr(problem.difficulty, "value", str(problem.difficulty))
    xp = xp_for_attempt(difficulty, score, passed, time_spent_sec, hints_used)

    already_solved = False
    if problem.id and attempt_id:
        try:
            already_solved = gam_repo.has_prior_passed_attempt(problem.id, attempt_id)
        except Exception:
            already_solved = False
    if already_solved:
        xp = int(round(xp * 0.25)) if passed else 0

    if xp:
        gam_repo.add_xp(
            xp,
            reason=f"{'re-solved' if passed and already_solved else 'solved' if passed else 'attempted'} {difficulty}",
            attempt_id=attempt_id,
            problem_id=problem.id,
        )

    context: dict = {
        "last_score": score,
        "last_passed": passed,
        "last_time_spent_sec": time_spent_sec,
        "last_hints_used": hints_used,
    }

    def gather(key, fn, default=0):
        try:
            context[key] = fn()
        except Exception:
            context[key] = default

    gather("total_xp", gam_repo.total_xp)
    gather("no_hint_solves", gam_repo.no_hint_solve_count)
    gather("dsa_patterns_solved", gam_repo.solved_dsa_pattern_count)
    gather("python_solved", lambda: gam_repo.solved_count_for_category("python_fundamentals"))
    gather("plan_completed", gam_repo.any_plan_completed, False)
    gather("simulation_passed", gam_repo.any_simulation_passed, False)
    gather("bookmark_count", gam_repo.bookmark_count)
    gather("custom_problem_count", gam_repo.custom_problem_count)
    gather("languages_solved", gam_repo.languages_solved_count)
    if passed and problem.id and attempt_id:
        gather("solved_after_fail", lambda: gam_repo.has_prior_failed_attempt(problem.id, attempt_id), False)

    try:
        stats = session_repo.get_stats()
        context["total_solved"] = stats.get("total_solved", 0)
        context["active_days_30"] = stats.get("active_days_30", 0)
        activity = session_repo.get_daily_activity(60)
        context["streak_days"] = current_streak_days([d.get("day", "") for d in activity])
    except Exception:
        pass

    try:
        unlocked = gam_repo.unlocked_keys()
    except Exception:
        unlocked = set()
    new = check_achievements(context, unlocked)
    for achievement in new:
        try:
            gam_repo.unlock(achievement.key)
        except Exception:
            pass
    return xp, new
