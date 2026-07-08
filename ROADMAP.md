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

---

## Near-Term — Foundation & Quality

Correctness and reach improvements that de-risk everything below them.

### Deterministic Test-Case Verification
The evaluation loop today relies on the LLM to judge correctness; the code
runner executes submissions but never asserts actual output against
`expected_output`, and when the LLM is offline every submission scores 0.5.
- Compare captured stdout / return values against `expected_output` per test case
- Report per-case pass/fail alongside the LLM's qualitative feedback
- Use deterministic results as the score floor/ceiling (an LLM can't "pass"
  code that fails its test cases)
- Prerequisite for fair XP/achievements and trustworthy simulation scorecards

### Cloud LLM Backend Option (Anthropic / OpenAI-compatible)
The `LLMClient` abstraction already supports pluggable backends; adding an
API-key backend dramatically widens the audience beyond local-LLM users.
- `LLM_BACKEND=anthropic` (or any OpenAI-compatible endpoint) via `.env`
- Local-first remains the default; document the privacy trade-off clearly
- Better structured-output reliability improves every feature downstream

### Code-Runner Sandbox Hardening
Current execution is a plain subprocess with the user's interpreter — fine
for self-authored code, insufficient once custom/shared problems exist.
- Resource limits (memory, CPU, process count), no-network execution
- Restricted filesystem visibility for the child process

---

## Near-Term — Features

### Gamification — XP & Achievements
Keeps motivation high across long preparation streaks.
- XP earned per problem solved, scaled by difficulty + score
- Level thresholds with titles (e.g. "Intern" → "Staff Engineer")
- 15+ defined achievements:
  - First Solve, 7-Day Streak, Perfect Score, Speed Demon (< 5 min)
  - DSA Master (solve all 10 patterns), Pythonista, Plan Finisher, …
- Toast notification on unlock via Textual's `notify()`
- Achievement gallery on the Progress screen
- XP history chart on the Progress screen

### Problem Bookmarking & Solution Library
Save and revisit favourite problems and solutions. (Promoted from
Longer-Term: cheap to build on existing notes/replay infrastructure,
high daily utility.)
- Bookmark button on every problem card
- "My Library" screen with bookmarked problems and user solutions
- Filter by tag, difficulty, category
- Compare user solution vs AI-optimal solution side-by-side

---

## Medium-Term

### Company-Specific Prep Profiles
Tailored problem sets for specific employers.
- `data/companies.json` — FAANG and top-tier companies with:
  - Common interview patterns (e.g. Amazon = OOP + behavioural, Google = graphs + DP)
  - Typical round structure and time limits
  - Difficulty distribution and known focuses
- Company browser screen with search
- One-click "Prepare for this company" → creates a targeted learning plan
- Integrates with Job Description screen for combined prep

### MCP Job-Search Tool Integration
Connects the app to live job market data.
- **Job search in-app**: `search_jobs` MCP tool surfaces listings by title/location
  directly in the Job Description screen — no copy-pasting required
- **Auto-load JD**: select a listing → `get_job_details` populates the JD text area
- **Company intelligence**: `get_company_data` enriches the company prep profile
- **Resume import**: `get_resume` MCP tool pulls structured resume data into the
  Resume Drill screen, replacing manual paste

### Custom Problem Creation
Let users define their own drill problems. (Promoted from Longer-Term:
unlocks sharing and personal drill banks; depends on sandbox hardening.)
- "New Problem" form in the TUI (title, description, examples, hints, solution)
- Stored with `source = "custom"` in the DB
- Included in random problem selection and review queue
- Export custom problems to JSON for sharing

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

### Multiple Language Support
Extend beyond Python to other common interview languages.
- JavaScript / TypeScript (Node.js runner)
- Go, Rust, Java stubs
- Language selector per problem; LLM evaluation adapts to chosen language
- Syntax highlighting theme per language in the code editor

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
