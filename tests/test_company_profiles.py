"""Tests for company interview profiles and targeted plan building."""

from __future__ import annotations

from codepractice.core.company_profiles import (
    build_company_plan,
    company_goal_text,
    company_intelligence_note,
    find_company_by_name,
    get_company,
    load_companies,
    search_companies,
)
from codepractice.config import DSA_PATTERNS

VALID_PATTERNS = {p["id"] for p in DSA_PATTERNS}


class TestDataset:
    def test_loads_companies(self):
        companies = load_companies()
        assert len(companies) >= 8

    def test_required_fields_present(self):
        for c in load_companies():
            assert c["id"] and c["name"]
            assert c["patterns"], c["id"]
            assert c["focus_areas"], c["id"]
            assert c["rounds"], c["id"]

    def test_patterns_reference_real_dsa_ids(self):
        for c in load_companies():
            for p in c["patterns"]:
                assert p in VALID_PATTERNS, f"{c['id']}: unknown pattern {p}"

    def test_difficulty_distributions_sum_to_one(self):
        for c in load_companies():
            dist = c["difficulty_distribution"]
            assert abs(sum(dist.values()) - 1.0) < 0.01, c["id"]


class TestSearch:
    def test_empty_query_returns_all(self):
        assert len(search_companies("")) == len(load_companies())

    def test_search_by_name(self):
        results = search_companies("goog")
        assert [c["id"] for c in results] == ["google"]

    def test_search_by_alias(self):
        results = search_companies("facebook")
        assert [c["id"] for c in results] == ["meta"]

    def test_search_case_insensitive(self):
        assert search_companies("STRIPE")[0]["id"] == "stripe"

    def test_no_match(self):
        assert search_companies("zzzcorp") == []

    def test_get_company(self):
        assert get_company("amazon")["name"] == "Amazon"
        assert get_company("nope") is None

    def test_find_by_free_text_name(self):
        assert find_company_by_name("Google")["id"] == "google"
        assert find_company_by_name("aws")["id"] == "amazon"
        assert find_company_by_name("") is None
        assert find_company_by_name("Unknown Startup") is None


class TestCompanyPlan:
    def test_plan_has_requested_duration(self):
        plan = build_company_plan(get_company("google"), 14)
        assert plan.duration_days == 14
        assert len(plan.daily_schedule) == 14

    def test_tasks_use_company_patterns(self):
        company = get_company("meta")
        plan = build_company_plan(company, 10)
        used = {d.tasks[0].problem_subcategory for d in plan.daily_schedule}
        assert used <= set(company["patterns"])

    def test_difficulty_matches_distribution_shape(self):
        """Databricks (50% hard) should schedule more hard days than Amazon (20%)."""
        hard_databricks = sum(
            1 for d in build_company_plan(get_company("databricks"), 30).daily_schedule
            if d.tasks[0].difficulty == "hard"
        )
        hard_amazon = sum(
            1 for d in build_company_plan(get_company("amazon"), 30).daily_schedule
            if d.tasks[0].difficulty == "hard"
        )
        assert hard_databricks > hard_amazon

    def test_estimated_minutes_from_profile(self):
        plan = build_company_plan(get_company("netflix"), 5)
        assert plan.daily_schedule[0].estimated_minutes == 60

    def test_title_names_the_company(self):
        plan = build_company_plan(get_company("stripe"), 7)
        assert "Stripe" in plan.title


class TestPromptHelpers:
    def test_goal_text_mentions_company_and_duration(self):
        text = company_goal_text(get_company("uber"), 14)
        assert "Uber" in text
        assert "14" in text

    def test_intelligence_note_contains_patterns_and_notes(self):
        note = company_intelligence_note(get_company("airbnb"))
        assert "Airbnb" in note
        assert "Common patterns" in note
        assert "Notes:" in note


class TestScreen:
    def test_companies_screen_imports(self):
        from codepractice.tui.screens.companies import CompaniesContent
        assert CompaniesContent is not None


class TestFreshness:
    def test_last_reviewed_stamp_present(self):
        from codepractice.core.company_profiles import get_last_reviewed
        stamp = get_last_reviewed()
        assert stamp and stamp[:4].isdigit()
