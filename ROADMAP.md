# CodePractice — Roadmap

Features planned for future iterations, roughly ordered by impact.

---

## Near-Term

### Interview Simulation Mode
A timed, no-hints practice mode that mirrors real interview conditions.
- Configurable session length (20 / 45 / 90 min)
- Countdown timer widget in the header (green → yellow → red)
- Hint button disabled; peeking at hints counts against score
- Problems drawn from job description or company profile
- Final scorecard with pass/fail verdict and category breakdown
- Stored separately from regular practice sessions for clean analytics

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

### Goal Evolution Tracking
Makes the learning plan truly adaptive over time.
- `goal_history` DB table: timestamped NL goal statements + plan summaries
- `codepractice goal "I want to focus more on system design now"` CLI command
- "Update Goal" button on the Learning Plan screen
- LLM reads full goal history to evolve the plan, explaining what changed
- Week-over-week goal drift summary in the Progress screen

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

### Vim / Emacs Keybindings in Code Editor
Reduces friction for users who live in modal editors.
- Toggle between Standard / Vim / Emacs modes in Settings
- Persisted per user profile
- `i` / `Esc` for insert/normal mode in Vim mode; `C-x C-s` equivalent in Emacs

---

## Longer-Term

### Multiple Language Support
Extend beyond Python to other common interview languages.
- JavaScript / TypeScript (Node.js runner)
- Go, Rust, Java stubs
- Language selector per problem; LLM evaluation adapts to chosen language
- Syntax highlighting theme per language in the code editor

### Problem Bookmarking & Solution Library
Save and revisit favourite problems and solutions.
- Bookmark button on every problem card
- "My Library" screen with bookmarked problems and user solutions
- Filter by tag, difficulty, category
- Compare user solution vs AI-optimal solution side-by-side

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

### Custom Problem Creation
Let users define their own drill problems.
- "New Problem" form in the TUI (title, description, examples, hints, solution)
- Stored with `source = "custom"` in the DB
- Included in random problem selection and review queue
- Export custom problems to JSON for sharing
