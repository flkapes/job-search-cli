# CodePractice — Roadmap

Features planned for future iterations, roughly ordered by impact.

> **Source of truth:** This roadmap is aspirational and may include ideas not yet
> released. For shipped capabilities, rely on `README.md` and in-app commands.

---

## Shipped (as of 2026-07-08)

### ✅ Implemented — Offline Problem Cache
- `codepractice prefetch --count N` warms and stores generated problems.
- Optional `--category` and `--difficulty` filtering.

### ✅ Implemented — Session Replay
- Progress screen rows open a replay modal with submitted code and AI feedback.

### ✅ Implemented — Personal Notes on Problems
- Per-problem notes persisted and surfaced across practice/review.

### ✅ Implemented — Weak-Area Auto-Drill
- "Fix My Gaps" launches targeted drilling from weak category detection.

### ✅ Implemented — Daily Digest Command
- `codepractice digest` prints streak/stats/review queue and optional AI tip.

### ✅ Implemented — Progress Markdown Export
- `codepractice export --format md` creates a Markdown progress report.

### ✅ Implemented — Suggested Approach Diff View
- Feedback can display parsed `optimized_solution` guidance after evaluation.

### ✅ Implemented — Personal Difficulty Rating
- 1–5 user difficulty rating stored on attempts and used in mismatch analysis.

### ✅ Implemented — Freeform Interview Questions + Drafts
- JD/Resume flows can generate non-coding interview questions.
- Draft answers persist via `question_drafts`.

### ✅ Implemented — Interview Simulation Mode
- Timed, no-hints sessions from the Dashboard with countdown timer,
  peek-penalty tracking, early finish, and end-of-session scorecard.
- Stored with `session_type = "interview_simulation"` for clean analytics.

### ✅ Implemented — Goal Evolution Tracking
- `goal_history` table, `codepractice goal "..."` CLI command,
  "Update Goal" action on the Learning Plan screen, and a goal-drift
  panel on the Progress screen.

### ✅ Implemented — Deterministic Test-Case Verification (2026-07-08)
- Test cases verify actual output vs `expected_output`; guardrails cap/floor
  LLM scores; offline scoring from real results; per-case results panel.

### ✅ Implemented — Gamification: XP & Achievements (2026-07-08)
- XP by difficulty × score with speed/no-hint bonuses, 8 level tiers,
  18 achievements with unlock toasts, Progress-screen gallery + XP chart.

### ✅ Implemented — Problem Bookmarking & My Library (2026-07-08)
- Star toggle (`B`), filterable library screen, side-by-side comparison of
  your best solution vs the AI-optimal solution.

### ✅ Implemented — Cloud LLM Backends (2026-07-08)
- `LLM_BACKEND=anthropic` (official SDK) or `openai`-compatible endpoints;
  API keys env-only; local-first remains the default.

### ✅ Implemented — Company-Specific Prep Profiles (2026-07-08)
- `data/companies.json` (10 companies), searchable browser, one-click
  targeted plan (LLM or deterministic fallback), JD-flow enrichment.

### ✅ Implemented — Custom Problem Creation (2026-07-08)
- New Problem form, `source='custom'`, inclusion in practice/review,
  `codepractice export-problems` / `import-problems`.

### ✅ Implemented — Multi-Language Practice (2026-07-08)
- JavaScript and Go runners with verified test cases, language selector +
  per-language highlighting, per-attempt language tracking.

---

## Near-Term

### Code-Runner Sandbox Hardening
Execution is a plain subprocess with the local toolchain — fine for
self-authored code, insufficient now that problems can be imported.
- Resource limits (memory, CPU, process count), no-network execution
- Restricted filesystem visibility for the child process

---

## Medium-Term

### MCP Job-Search Tool Integration
Connects the app to live job market data.
- **Job search in-app**: `search_jobs` MCP tool surfaces listings by title/location
  directly in the Job Description screen — no copy-pasting required
- **Auto-load JD**: select a listing → `get_job_details` populates the JD text area
- **Company intelligence**: `get_company_data` enriches the company prep profile
- **Resume import**: `get_resume` MCP tool pulls structured resume data into the
  Resume Drill screen, replacing manual paste

### Vim / Emacs Keybindings in Code Editor
Reduces friction for users who live in modal editors.
- Toggle between Standard / Vim / Emacs modes in Settings
- Persisted per user profile
- `i` / `Esc` for insert/normal mode in Vim mode; `C-x C-s` equivalent in Emacs

---

## Big Bets

Larger directional investments that would change what the product *is*,
not just add to it.

### AI Mock Interviewer
The single biggest differentiator vs. LeetCode-style grinding: a
conversational interviewer persona wrapped around the existing practice loop.
- Interviewer introduces the problem verbally, answers clarifying questions
- Follow-up probes: "What's the time complexity?", "Can you optimize space?"
- Interruptions and hints modeled on real interviewer behaviour
- Post-session transcript + rubric evaluation (communication, correctness,
  optimization, testing instincts)
- Builds directly on chat_service + interview simulation mode

### Behavioural Interview Track
Freeform question generation already exists — extend it to a full track.
- STAR-format answer coaching with per-dimension rubric scoring
- Question banks by seniority and role type
- Draft answers evolve across attempts; spaced repetition for stories

### System Design Track
Text-based system design practice, LLM-evaluated.
- Prompt bank (design a URL shortener, rate limiter, news feed …)
- Structured answer template (requirements → estimates → API → data → scaling)
- LLM rubric evaluation with follow-up questions
- Ties into learning plans and company profiles for senior-role prep

### Job Application Tracker
The repo is called *job-search-cli* — close the loop from practice to search.
- Track applications: company, role, stage, dates, contacts, outcomes
- Link each application to its JD prep, company profile, and sim sessions
- Pipeline view + reminders for follow-ups
- Turns the app from "interview prep" into an end-to-end job-search companion

### Distribution & Release Engineering
- Publish to PyPI (`pipx install codepractice`), versioned releases + changelog
- Ratchet CI coverage gate up from 40% toward 70%
- Screenshots/asciinema demo in README for discoverability

---

## Longer-Term

### Additional Language Runners
JavaScript and Go shipped 2026-07-08 — extend the runner registry further.
- TypeScript (tsx), Rust, and Java adapters
- Language-specific starter stubs per problem

### Daily Reminder / Notification System
Nudges users to keep their streak alive.
- Optional cron-based desktop notification (Linux: `notify-send`, macOS: `osascript`)
- `codepractice remind --at 09:00` CLI command to register
- Review due count included in the notification message

### Terminal Recording & Sharing
Show off completed sessions.
- `asciinema` integration: record a practice session as a shareable `.cast` file
- `codepractice record` command wraps the TUI in an asciinema session
- Automatic upload to asciinema.org (opt-in)

### Anonymised Peer Benchmarking
Lightweight social accountability.
- Opt-in telemetry uploads solve rate, avg score, and streak (no code)
- "How do you compare?" section on the Progress screen
- Percentile rank among users at the same experience level
- ⚠️ Requires a hosted backend, which cuts against the "no data sent to the
  cloud" promise in the README — needs a deliberate privacy design (or a
  local-only "compare against published percentiles" variant) before pickup.
