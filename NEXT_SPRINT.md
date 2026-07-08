# Next Sprint — Implementation Queue

Features currently pending implementation, in rough priority order.

> **Source of truth:** `ROADMAP.md` is aspirational and includes future ideas.
> `README.md` reflects currently released capabilities.

---

## Done (completed 2026-05-22)

- ✅ **Offline Problem Cache** (`codepractice prefetch --count N`) with optional
  `--category` and `--difficulty` filters.
- ✅ **Session Replay** modal from Progress screen attempt rows.
- ✅ **Personal Notes on Problems** persisted via `problems.user_notes`.
- ✅ **Weak-Area Auto-Drill** (“Fix My Gaps” targeted drill flow).
- ✅ **Daily Digest Command** (`codepractice digest`) with LLM-offline fallback.
- ✅ **Progress Markdown Export** (`codepractice export --format md`).
- ✅ **Code Diff / Suggested Approach View** using parsed `optimized_solution`.
- ✅ **Per-Problem Personal Difficulty Rating** (1–5) stored on attempts.
- ✅ **Freeform Interview Question Generation** (JD/Resume) with draft persistence.

### Verification snapshot (code paths)

- CLI commands: `codepractice/main.py` (`prefetch`, `digest`, `export`). 
- Replay + weak-area drill UI: `codepractice/tui/screens/progress.py`.
- Diff view + personal difficulty rating UI: `codepractice/tui/screens/practice.py`.
- Freeform question UI + draft modal: `codepractice/tui/screens/job_desc.py`,
  `codepractice/tui/screens/resume_drill.py`.
- Persistence: migrations in `codepractice/db/migrations/005_*.sql`,
  `006_*.sql`, `007_*.sql`; repositories in `codepractice/db/repositories/`.

---

## Also done

- ✅ **Interview Simulation Mode** (completed 2026-05-22) — dashboard entry,
  countdown timer + lock behavior, hint-peek penalty tracking, scorecard
  aggregation, `session_type = "interview_simulation"` persistence
  (migration `009_*.sql`).
- ✅ **Goal Evolution Tracking** (completed 2026-05-22) — `goal_history`
  persistence (migration `008_*.sql`), `codepractice goal "..."` CLI command,
  "Update Goal" action on the Learning Plan screen, goal-drift panel in
  Progress.

---

## 1. Deterministic Test-Case Verification

**Location:** `codepractice/utils/code_runner.py` + answer evaluator + practice flow

Make correctness verifiable instead of purely LLM-judged.
`run_with_test_cases` currently injects `_expected` into the script but never
compares it against actual output — "passed" only means exit code 0. When the
LLM is offline, every submission scores 0.5 regardless of correctness.

**Implementation notes:**
- Compare captured stdout / function return values against `expected_output`
  per test case; report per-case pass/fail
- Feed deterministic results into `AnswerEvaluatorService` as a score
  floor/ceiling — the LLM refines, it doesn't overrule failing tests
- Show a per-test-case results table in the practice feedback panel
- Prerequisite for fair XP (item 2) and trustworthy simulation scorecards

---

## 2. Gamification — XP & Achievements

**Location:** Progress screen + attempt completion flow

Keeps motivation high across long preparation streaks.
(Do after item 1 so XP is grounded in real correctness.)

**Implementation notes:**
- Add XP accrual rules by difficulty × score
- Persist level + XP history in new tables
- Add achievement unlock engine with milestone definitions
- Show unlock toasts and an achievements gallery screen section
- Add XP trend chart in Progress

---

## 3. Problem Bookmarking & Solution Library

**Location:** Practice + new "My Library" screen

Save and revisit favorite problems and your own solutions.
(Promoted: small schema + one screen, builds on existing notes/replay.)

**Implementation notes:**
- Add bookmark toggle in problem card
- Persist saved problem IDs and associated user solutions
- Create library screen with filter/sort by tag/difficulty/category
- Add side-by-side comparison with AI suggested solution

---

## 4. Cloud LLM Backend Option

**Location:** `codepractice/llm/client.py` + config + setup wizard

Add an Anthropic / OpenAI-compatible API backend alongside Ollama and
LM Studio. Local-first stays the default; widens the audience to users
without a local LLM and improves structured-output reliability everywhere.

**Implementation notes:**
- New `LLMBackend` subclass reading API key from `.env` (never persisted to DB)
- Extend `codepractice check` and the setup wizard with the new backend
- Document the privacy trade-off in README (local remains the default)

---

## 5. Company-Specific Prep Profiles

**Location:** New company browser + Learning Plan integrations

Tailored problem sets for specific employers.

**Implementation notes:**
- Add `data/companies.json` with interview pattern metadata
- Build searchable company browser view
- One-click targeted plan generation from company profile
- Integrate with JD flow for combined prep

---

## 6. Custom Problem Creation

**Location:** New problem form + problem bank + review queue

Let users author their own drill problems.

**Implementation notes:**
- "New Problem" form in the TUI (title, description, examples, hints, solution)
- Store with `source = "custom"`; include in random selection + review queue
- Export/import custom problems as JSON
- Harden the code-runner sandbox (resource limits, no network) before
  supporting *imported* problems

---

## 7. Multi-Language Practice Support

**Location:** Practice screen + code runner + evaluator

Extend beyond Python to common interview languages.

**Implementation notes:**
- Add language selector on problem card
- Add runner/evaluator adapters for JavaScript and Go first
- Extend prompting and syntax highlighting per language
- Ensure persistence tracks chosen language per attempt
