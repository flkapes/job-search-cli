from __future__ import annotations

from datetime import datetime, timedelta

from codepractice.db.repositories import ProblemRepository, SessionRepository
from codepractice.tui.screens.practice import PracticeContent


def test_session_type_and_metadata_persist(tmp_db):
    repo = SessionRepository(tmp_db)
    sid = repo.start_session(
        session_type="interview_simulation",
        metadata={"duration_sec": 1800, "simulation_mode": True},
    )
    row = repo.get_session(sid)
    assert row is not None
    assert row["session_type"] == "interview_simulation"
    assert "duration_sec" in (row.get("metadata_json") or "")


def test_scorecard_aggregation_inputs(tmp_db):
    p_repo = ProblemRepository(tmp_db)
    s_repo = SessionRepository(tmp_db)

    p1 = p_repo.create({"category": "dsa", "subcategory": "arrays", "title": "A", "description": "D"})
    p2 = p_repo.create({"category": "python_fundamentals", "subcategory": "oop", "title": "B", "description": "D"})
    sid = s_repo.start_session(session_type="interview_simulation")

    s_repo.record_attempt({"session_id": sid, "problem_id": p1, "ai_score": 0.8, "passed": True})
    s_repo.record_attempt({"session_id": sid, "problem_id": p2, "ai_score": 0.4, "passed": False})

    card = s_repo.get_scorecard(sid)
    assert card["attempted"] == 2
    assert card["solved"] == 1
    assert len(card["category_breakdown"]) == 2


def test_timer_state_transitions():
    content = PracticeContent(simulation_mode=True, simulation_duration_sec=1800)
    content._simulation_deadline = datetime.now() + timedelta(minutes=20)
    _, color = content._timer_state()
    assert color == "green"

    content._simulation_deadline = datetime.now() + timedelta(minutes=10)
    _, color = content._timer_state()
    assert color == "yellow"

    content._simulation_deadline = datetime.now() + timedelta(minutes=3)
    _, color = content._timer_state()
    assert color == "red"


def test_hint_blocking_and_peek_penalty_in_simulation_mode():
    content = PracticeContent(simulation_mode=True)
    before = content._peek_attempts
    content.action_show_hint()
    assert content._peek_attempts == before + 1
