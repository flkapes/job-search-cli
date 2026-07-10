"""Tests for XP rules, levels, achievements, and the reward flow."""

from __future__ import annotations

from datetime import date

from codepractice.core.gamification import (
    ACHIEVEMENTS,
    award_attempt,
    check_achievements,
    current_streak_days,
    level_for_xp,
    xp_for_attempt,
)
from codepractice.core.models import Problem
from codepractice.db.repositories import GamificationRepository, ProblemRepository, SessionRepository


class TestXPForAttempt:
    def test_scales_with_difficulty(self):
        easy = xp_for_attempt("easy", 1.0, True, hints_used=1)
        medium = xp_for_attempt("medium", 1.0, True, hints_used=1)
        hard = xp_for_attempt("hard", 1.0, True, hints_used=1)
        assert easy < medium < hard

    def test_scales_with_score(self):
        low = xp_for_attempt("medium", 0.5, True, hints_used=1)
        high = xp_for_attempt("medium", 1.0, True, hints_used=1)
        assert low < high

    def test_failed_attempt_earns_fraction(self):
        failed = xp_for_attempt("medium", 0.6, False)
        passed = xp_for_attempt("medium", 0.6, True, hints_used=1)
        assert 0 < failed < passed

    def test_speed_bonus(self):
        fast = xp_for_attempt("medium", 0.8, True, time_spent_sec=100, hints_used=1)
        slow = xp_for_attempt("medium", 0.8, True, time_spent_sec=900, hints_used=1)
        assert fast == slow + 5

    def test_no_hints_bonus(self):
        clean = xp_for_attempt("medium", 0.8, True, time_spent_sec=900, hints_used=0)
        hinted = xp_for_attempt("medium", 0.8, True, time_spent_sec=900, hints_used=2)
        assert clean == hinted + 5

    def test_unknown_difficulty_defaults_to_medium(self):
        assert xp_for_attempt("weird", 1.0, True, hints_used=1) == xp_for_attempt("medium", 1.0, True, hints_used=1)

    def test_score_clamped(self):
        assert xp_for_attempt("medium", 5.0, True, hints_used=1) == xp_for_attempt("medium", 1.0, True, hints_used=1)


class TestLevels:
    def test_zero_xp_is_intern(self):
        info = level_for_xp(0)
        assert info.level == 1
        assert info.title == "Intern"

    def test_thresholds_promote(self):
        assert level_for_xp(100).title == "Junior Engineer"
        assert level_for_xp(299).title == "Junior Engineer"
        assert level_for_xp(1000).title == "Staff Engineer"

    def test_max_level(self):
        info = level_for_xp(999999)
        assert info.title == "Distinguished Engineer"
        assert info.next_threshold is None
        assert info.progress_to_next == 1.0

    def test_progress_fraction(self):
        info = level_for_xp(200)  # between 100 and 300
        assert 0.0 < info.progress_to_next < 1.0


class TestCurrentStreak:
    def test_empty_is_zero(self):
        assert current_streak_days([]) == 0

    def test_consecutive_days_counted(self):
        today = date(2026, 7, 8)
        days = ["2026-07-08", "2026-07-07", "2026-07-06"]
        assert current_streak_days(days, today=today) == 3

    def test_streak_survives_if_yesterday(self):
        today = date(2026, 7, 8)
        days = ["2026-07-07", "2026-07-06"]
        assert current_streak_days(days, today=today) == 2

    def test_gap_breaks_streak(self):
        today = date(2026, 7, 8)
        days = ["2026-07-08", "2026-07-06"]
        assert current_streak_days(days, today=today) == 1

    def test_stale_activity_is_zero(self):
        today = date(2026, 7, 8)
        assert current_streak_days(["2026-07-01"], today=today) == 0


class TestCheckAchievements:
    def test_first_solve(self):
        new = check_achievements({"total_solved": 1}, set())
        assert any(a.key == "first_solve" for a in new)

    def test_already_unlocked_not_returned(self):
        new = check_achievements({"total_solved": 1}, {"first_solve"})
        assert not any(a.key == "first_solve" for a in new)

    def test_perfect_score_requires_pass(self):
        new = check_achievements({"last_score": 1.0, "last_passed": False}, set())
        assert not any(a.key == "perfect_score" for a in new)
        new = check_achievements({"last_score": 1.0, "last_passed": True}, set())
        assert any(a.key == "perfect_score" for a in new)

    def test_speed_demon(self):
        ctx = {"last_passed": True, "last_time_spent_sec": 200}
        assert any(a.key == "speed_demon" for a in check_achievements(ctx, set()))

    def test_dsa_master_requires_all_patterns(self):
        assert not any(a.key == "dsa_master" for a in check_achievements({"dsa_patterns_solved": 9}, set()))
        assert any(a.key == "dsa_master" for a in check_achievements({"dsa_patterns_solved": 10}, set()))

    def test_level_staff_from_xp(self):
        assert any(a.key == "level_staff" for a in check_achievements({"total_xp": 1000}, set()))

    def test_at_least_fifteen_achievements_defined(self):
        assert len(ACHIEVEMENTS) >= 15
        assert len({a.key for a in ACHIEVEMENTS}) == len(ACHIEVEMENTS)


class TestGamificationRepository:
    def test_add_and_total_xp(self, tmp_db):
        repo = GamificationRepository(tmp_db)
        assert repo.total_xp() == 0
        repo.add_xp(25, reason="solved medium")
        repo.add_xp(10, reason="solved easy")
        assert repo.total_xp() == 35

    def test_unlock_idempotent(self, tmp_db):
        repo = GamificationRepository(tmp_db)
        assert repo.unlock("first_solve") is True
        assert repo.unlock("first_solve") is False
        assert repo.unlocked_keys() == {"first_solve"}

    def test_xp_by_day_groups(self, tmp_db):
        repo = GamificationRepository(tmp_db)
        repo.add_xp(10)
        repo.add_xp(15)
        days = repo.xp_by_day(7)
        assert len(days) == 1
        assert days[0]["xp"] == 25

    def test_context_queries_empty_db(self, tmp_db):
        repo = GamificationRepository(tmp_db)
        assert repo.no_hint_solve_count() == 0
        assert repo.solved_dsa_pattern_count() == 0
        assert repo.solved_count_for_category("python_fundamentals") == 0
        assert repo.bookmark_count() == 0
        assert repo.custom_problem_count() == 0
        assert repo.languages_solved_count() == 0
        assert repo.any_plan_completed() is False
        assert repo.any_simulation_passed() is False


class TestAwardAttempt:
    def _setup(self, tmp_db):
        problems = ProblemRepository(tmp_db)
        sessions = SessionRepository(tmp_db)
        gam = GamificationRepository(tmp_db)
        pid = problems.create({"category": "dsa", "subcategory": "two_pointers",
                               "title": "T", "description": "d", "difficulty": "medium"})
        sid = sessions.start_session("free")
        return problems, sessions, gam, pid, sid

    def test_award_records_xp_and_first_solve(self, tmp_db):
        problems, sessions, gam, pid, sid = self._setup(tmp_db)
        aid = sessions.record_attempt({
            "session_id": sid, "problem_id": pid, "ai_score": 0.9,
            "passed": True, "time_spent_sec": 100, "hints_used": 0,
        })
        problem = Problem.from_db(problems.get_by_id(pid))
        xp, new = award_attempt(gam, sessions, problem, aid, 0.9, True,
                                time_spent_sec=100, hints_used=0)
        assert xp > 0
        assert gam.total_xp() == xp
        assert any(a.key == "first_solve" for a in new)
        assert "first_solve" in gam.unlocked_keys()

    def test_second_award_does_not_reunlock(self, tmp_db):
        problems, sessions, gam, pid, sid = self._setup(tmp_db)
        problem = Problem.from_db(problems.get_by_id(pid))
        for _ in range(2):
            aid = sessions.record_attempt({
                "session_id": sid, "problem_id": pid, "ai_score": 0.9,
                "passed": True, "time_spent_sec": 100, "hints_used": 0,
            })
            xp, new = award_attempt(gam, sessions, problem, aid, 0.9, True,
                                    time_spent_sec=100, hints_used=0)
        assert not any(a.key == "first_solve" for a in new)

    def test_comeback_unlocks_after_prior_failure(self, tmp_db):
        problems, sessions, gam, pid, sid = self._setup(tmp_db)
        problem = Problem.from_db(problems.get_by_id(pid))
        fail_id = sessions.record_attempt({
            "session_id": sid, "problem_id": pid, "ai_score": 0.2, "passed": False,
        })
        award_attempt(gam, sessions, problem, fail_id, 0.2, False)
        assert "comeback" not in gam.unlocked_keys()

        pass_id = sessions.record_attempt({
            "session_id": sid, "problem_id": pid, "ai_score": 0.9, "passed": True,
        })
        _, new = award_attempt(gam, sessions, problem, pass_id, 0.9, True)
        assert any(a.key == "comeback" for a in new)


class TestAntiFarming:
    def _setup(self, tmp_db):
        problems = ProblemRepository(tmp_db)
        sessions = SessionRepository(tmp_db)
        gam = GamificationRepository(tmp_db)
        pid = problems.create({"category": "dsa", "subcategory": "bfs",
                               "title": "T", "description": "d", "difficulty": "medium"})
        sid = sessions.start_session("free")
        return problems, sessions, gam, pid, sid

    def _attempt_and_award(self, sessions, gam, problems, pid, sid, passed, score=0.9):
        aid = sessions.record_attempt({
            "session_id": sid, "problem_id": pid, "ai_score": score,
            "passed": passed, "time_spent_sec": 400, "hints_used": 1,
        })
        problem = Problem.from_db(problems.get_by_id(pid))
        xp, _ = award_attempt(gam, sessions, problem, aid, score, passed,
                              time_spent_sec=400, hints_used=1)
        return xp

    def test_repeat_solve_pays_quarter(self, tmp_db):
        problems, sessions, gam, pid, sid = self._setup(tmp_db)
        first = self._attempt_and_award(sessions, gam, problems, pid, sid, passed=True)
        repeat = self._attempt_and_award(sessions, gam, problems, pid, sid, passed=True)
        assert first > 0
        assert repeat == int(round(first * 0.25))

    def test_failing_a_solved_problem_pays_nothing(self, tmp_db):
        problems, sessions, gam, pid, sid = self._setup(tmp_db)
        self._attempt_and_award(sessions, gam, problems, pid, sid, passed=True)
        before = gam.total_xp()
        xp = self._attempt_and_award(sessions, gam, problems, pid, sid, passed=False, score=0.3)
        assert xp == 0
        assert gam.total_xp() == before

    def test_first_fail_still_pays_fraction(self, tmp_db):
        problems, sessions, gam, pid, sid = self._setup(tmp_db)
        xp = self._attempt_and_award(sessions, gam, problems, pid, sid, passed=False, score=0.4)
        assert xp > 0

    def test_grinding_cannot_beat_one_real_solve(self, tmp_db):
        problems, sessions, gam, pid, sid = self._setup(tmp_db)
        first = self._attempt_and_award(sessions, gam, problems, pid, sid, passed=True)
        farmed = sum(
            self._attempt_and_award(sessions, gam, problems, pid, sid, passed=True)
            for _ in range(4)
        )
        assert farmed <= first
