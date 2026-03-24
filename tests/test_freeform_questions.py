"""Tests for freeform interview question generation — Feature 9."""

from __future__ import annotations

from codepractice.db.repositories.question_drafts import QuestionDraftsRepository
from codepractice.llm.client import LLMClient, LLMError
from codepractice.llm.prompts.problem_gen import freeform_questions_prompt
from codepractice.llm.services.problem_generator import ProblemGeneratorService

_FREEFORM_JSON = """[
  {
    "question": "Describe your approach to database indexing.",
    "type": "technical",
    "follow_ups": ["When would you avoid an index?", "How does B-tree indexing work?"]
  },
  {
    "question": "Tell me about a time you resolved a production incident.",
    "type": "behavioural",
    "follow_ups": ["How did you prevent recurrence?"]
  }
]"""


class MockLLMClient(LLMClient):
    def __init__(self, response: str = "", fail: bool = False):
        self._response = response
        self._fail = fail
        self.model = "mock"
        self.base_url = "http://mock"

    def health_check(self) -> bool:
        return not self._fail

    def list_models(self) -> list[str]:
        return ["mock"]

    def chat_sync(self, messages, **kwargs) -> str:
        if self._fail:
            raise LLMError("offline")
        return self._response

    def stream_chat(self, messages, **kwargs):
        if self._fail:
            raise LLMError("offline")
        yield self._response


# ── Prompt builder ─────────────────────────────────────────────────────────────

class TestFreeformQuestionsPrompt:
    def test_returns_two_messages(self):
        msgs = freeform_questions_prompt("jd", "Looking for backend engineer", ["technical"], 3)
        assert len(msgs) == 2

    def test_system_user_roles(self):
        msgs = freeform_questions_prompt("jd", "text", ["technical"], 2)
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_count_in_prompt(self):
        msgs = freeform_questions_prompt("jd", "text", ["technical"], 4)
        assert "4" in msgs[1]["content"]

    def test_question_types_in_prompt(self):
        msgs = freeform_questions_prompt("jd", "text", ["system_design", "behavioural"], 2)
        content = msgs[1]["content"].lower()
        assert "system_design" in content or "system design" in content
        assert "behavioural" in content or "behavioral" in content

    def test_source_text_in_prompt(self):
        msgs = freeform_questions_prompt("jd", "hire a python developer", ["technical"], 2)
        assert "python developer" in msgs[1]["content"].lower()

    def test_resume_source_text_in_prompt(self):
        msgs = freeform_questions_prompt("resume", "Built a Redis rate limiter", ["technical"], 2)
        assert "redis rate limiter" in msgs[1]["content"].lower()

    def test_long_text_truncated(self):
        long_text = "x" * 10000
        msgs = freeform_questions_prompt("jd", long_text, ["technical"], 2)
        assert len(msgs[1]["content"]) < 10000

    def test_json_schema_includes_follow_ups(self):
        msgs = freeform_questions_prompt("jd", "text", ["technical"], 2)
        assert "follow_ups" in msgs[1]["content"]

    def test_json_schema_includes_question_field(self):
        msgs = freeform_questions_prompt("jd", "text", ["technical"], 2)
        assert "question" in msgs[1]["content"]

    def test_json_schema_includes_type_field(self):
        msgs = freeform_questions_prompt("jd", "text", ["technical"], 2)
        assert '"type"' in msgs[1]["content"] or "'type'" in msgs[1]["content"] or "type" in msgs[1]["content"]


# ── Service ────────────────────────────────────────────────────────────────────

class TestGenerateFreeformQuestions:
    def test_returns_list_of_questions(self):
        svc = ProblemGeneratorService(MockLLMClient(response=_FREEFORM_JSON))
        questions = svc.generate_freeform_questions(
            source="jd",
            text="Backend Python engineer role",
            question_types=["technical", "behavioural"],
            count=2,
        )
        assert isinstance(questions, list)
        assert len(questions) == 2

    def test_each_question_has_required_fields(self):
        svc = ProblemGeneratorService(MockLLMClient(response=_FREEFORM_JSON))
        questions = svc.generate_freeform_questions("jd", "text", ["technical"], 2)
        for q in questions:
            assert "question" in q
            assert "type" in q
            assert "follow_ups" in q
            assert isinstance(q["follow_ups"], list)

    def test_returns_empty_list_on_llm_failure(self):
        svc = ProblemGeneratorService(MockLLMClient(fail=True))
        assert svc.generate_freeform_questions("jd", "text", ["technical"], 2) == []

    def test_returns_empty_list_on_invalid_json(self):
        svc = ProblemGeneratorService(MockLLMClient(response="not json"))
        assert svc.generate_freeform_questions("jd", "text", ["technical"], 2) == []

    def test_preserves_question_type(self):
        single = '[{"question": "Q", "type": "conceptual", "follow_ups": ["F"]}]'
        svc = ProblemGeneratorService(MockLLMClient(response=single))
        questions = svc.generate_freeform_questions("resume", "text", ["conceptual"], 1)
        assert len(questions) == 1
        assert questions[0]["type"] == "conceptual"

    def test_skips_items_missing_question_field(self):
        bad_json = '[{"type": "technical", "follow_ups": []}, {"question": "Good Q", "type": "technical", "follow_ups": []}]'
        svc = ProblemGeneratorService(MockLLMClient(response=bad_json))
        questions = svc.generate_freeform_questions("jd", "text", ["technical"], 2)
        assert len(questions) == 1


# ── QuestionDraftsRepository ───────────────────────────────────────────────────

class TestQuestionDraftsRepository:
    def test_save_and_get_draft(self, tmp_db):
        repo = QuestionDraftsRepository(tmp_db)
        repo.save_draft("hash123", "jd", "My detailed answer here")
        draft = repo.get_draft("hash123")
        assert draft is not None
        assert draft["draft_text"] == "My detailed answer here"
        assert draft["source_type"] == "jd"

    def test_nonexistent_returns_none(self, tmp_db):
        repo = QuestionDraftsRepository(tmp_db)
        assert repo.get_draft("nonexistent") is None

    def test_update_overwrites_draft(self, tmp_db):
        repo = QuestionDraftsRepository(tmp_db)
        repo.save_draft("hash456", "resume", "First draft")
        repo.save_draft("hash456", "resume", "Revised draft")
        draft = repo.get_draft("hash456")
        assert draft["draft_text"] == "Revised draft"

    def test_upsert_no_duplicate_for_same_hash(self, tmp_db):
        repo = QuestionDraftsRepository(tmp_db)
        repo.save_draft("same", "jd", "v1")
        repo.save_draft("same", "jd", "v2")
        drafts = repo.list_drafts_for_source("jd")
        assert len(drafts) == 1

    def test_list_drafts_for_source(self, tmp_db):
        repo = QuestionDraftsRepository(tmp_db)
        repo.save_draft("h1", "jd", "Answer 1")
        repo.save_draft("h2", "jd", "Answer 2")
        repo.save_draft("h3", "resume", "Answer 3")

        jd_drafts = repo.list_drafts_for_source("jd")
        assert len(jd_drafts) == 2
        assert all(d["source_type"] == "jd" for d in jd_drafts)

    def test_delete_draft(self, tmp_db):
        repo = QuestionDraftsRepository(tmp_db)
        repo.save_draft("del_me", "jd", "temp")
        repo.delete_draft("del_me")
        assert repo.get_draft("del_me") is None

    def test_delete_nonexistent_is_noop(self, tmp_db):
        repo = QuestionDraftsRepository(tmp_db)
        repo.delete_draft("ghost")  # should not raise

    def test_list_empty_source_returns_empty(self, tmp_db):
        repo = QuestionDraftsRepository(tmp_db)
        assert repo.list_drafts_for_source("jd") == []

    def test_draft_has_updated_at(self, tmp_db):
        repo = QuestionDraftsRepository(tmp_db)
        repo.save_draft("ts_test", "jd", "answer")
        draft = repo.get_draft("ts_test")
        assert "updated_at" in draft
        assert draft["updated_at"]
