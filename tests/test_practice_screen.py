from codepractice.tui.screens.practice import PracticeContent


def test_action_submit_code_only_runs_in_coding_phase(monkeypatch):
    widget = PracticeContent()
    calls = {"count": 0}

    def fake_submit():
        calls["count"] += 1

    monkeypatch.setattr(widget, "_submit_code", fake_submit)

    for phase in ("loading", "problem", "feedback"):
        widget.current_phase = phase
        widget.action_submit_code()

    assert calls["count"] == 0

    widget.current_phase = "coding"
    widget.action_submit_code()

    assert calls["count"] == 1


def test_action_submit_code_triggers_coding_to_feedback_transition(monkeypatch):
    widget = PracticeContent()
    transitions: list[str] = []

    def fake_submit():
        widget._show_phase("feedback")

    def fake_show_phase(phase: str):
        transitions.append(phase)
        widget.current_phase = phase

    monkeypatch.setattr(widget, "_submit_code", fake_submit)
    monkeypatch.setattr(widget, "_show_phase", fake_show_phase)

    widget.current_phase = "coding"
    widget.action_submit_code()

    assert transitions == ["feedback"]
    assert widget.current_phase == "feedback"


def test_submit_paths_noop_outside_coding_phase(monkeypatch):
    widget = PracticeContent()
    calls = {"count": 0}

    def fake_submit():
        calls["count"] += 1

    monkeypatch.setattr(widget, "_submit_code", fake_submit)

    widget.current_phase = "feedback"
    widget.on_code_editor_code_submitted(None)

    assert calls["count"] == 0
