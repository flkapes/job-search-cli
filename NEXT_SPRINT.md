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

## 1. Interview Simulation Mode

**Location:** Practice flow (new mode toggle)

A timed, no-hints practice mode that mirrors real interview conditions.

**Implementation notes:**
- Add session mode selector for normal vs interview simulation
- Disable hints in simulation mode and track any peek attempts
- Add countdown timer in header with state colors
- Generate end-of-session scorecard with pass/fail + category breakdown
- Store with dedicated `session_type = "interview_simulation"`

---

## 2. Gamification — XP & Achievements

**Location:** Progress screen + attempt completion flow

Keeps motivation high across long preparation streaks.

**Implementation notes:**
- Add XP accrual rules by difficulty × score
- Persist level + XP history in new tables
- Add achievement unlock engine with milestone definitions
- Show unlock toasts and an achievements gallery screen section
- Add XP trend chart in Progress

---

## 3. Goal Evolution Tracking

**Location:** Learning Plan + Progress + CLI

Makes the learning plan truly adaptive over time.

**Implementation notes:**
- Add `goal_history` persistence and retrieval
- Add CLI command to update goal text and trigger plan evolution
- Add "Update Goal" action in learning plan UI
- Surface week-over-week drift summary in Progress

---

## 4. Company-Specific Prep Profiles

**Location:** New company browser + Learning Plan integrations

Tailored problem sets for specific employers.

**Implementation notes:**
- Add `data/companies.json` with interview pattern metadata
- Build searchable company browser view
- One-click targeted plan generation from company profile
- Integrate with JD flow for combined prep

---

## 5. Multi-Language Practice Support

**Location:** Practice screen + code runner + evaluator

Extend beyond Python to common interview languages.

**Implementation notes:**
- Add language selector on problem card
- Add runner/evaluator adapters for JavaScript and Go first
- Extend prompting and syntax highlighting per language
- Ensure persistence tracks chosen language per attempt

---

## 6. Problem Bookmarking & Solution Library

**Location:** Practice + new "My Library" screen

Save and revisit favorite problems and your own solutions.

**Implementation notes:**
- Add bookmark toggle in problem card
- Persist saved problem IDs and associated user solutions
- Create library screen with filter/sort by tag/difficulty/category
- Add side-by-side comparison with AI suggested solution
