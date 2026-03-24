# Next Sprint — Implementation Queue

Features ready to build, in rough priority order. All are low-risk, additive,
and touch existing data/services with minimal new infrastructure.

---

## 1. Offline Problem Cache

**Command:** `codepractice prefetch --count 20`

Hit the LLM once to pre-generate and store problems while it's warm. Normal
practice then works even when Ollama is cold or unavailable.

**Implementation notes:**
- Loop `ProblemGeneratorService` N times across categories/difficulties
- Write results to `problems` table with `source = "ai_generated"`
- Show a Rich progress bar during generation
- Add `--category` and `--difficulty` flags for targeted prefetching
- No new DB schema needed

---

## 2. Session Replay

**Location:** Progress screen — click any past attempt row to open a detail view

Show the user's submitted code and the AI feedback they received, side by side.
All data already lives in `problem_attempts`. Zero new storage, pure display.

**Implementation notes:**
- Add a `ReplayModal` (Textual `ModalScreen`) with two panels:
  left = `CodeEditor` (read-only), right = `StreamingOutput` (static text)
- `DataTable` row selection on the Progress screen triggers the modal
- Pull `user_code` and `ai_feedback` from the attempt row by ID
- Include problem title, score, hints used, and time spent in a header bar

---

## 3. Personal Notes on Problems

**Location:** Problem card — small collapsible "My Notes" section

A persistent freeform text field per problem. Surfaces when the same problem
appears again (practice or review mode).

**Implementation notes:**
- Migration: `ALTER TABLE problems ADD COLUMN user_notes TEXT DEFAULT ''`
- `ProblemRepository.save_note(problem_id, text)` and `get_note(problem_id)`
- `ProblemCard` widget gains a collapsible `TextArea` at the bottom
- Auto-save on blur (no explicit save button)
- Show note in the replay modal too

---

## 4. Weak-Area Auto-Drill

**Location:** Progress screen — "Fix My Gaps" button

Calls the existing `get_weak_areas()` function, then launches practice
pre-filtered to that category/subcategory. Wires two things that already exist
but aren't connected.

**Implementation notes:**
- Button appears only when `get_category_scores()` returns ≥ 1 area with
  2+ attempts and avg score < 0.6
- Passes `category` and `subcategory` to `PracticeContent._load_next_problem()`
- Label shows which area is being drilled: "Drilling: dsa / dynamic_programming"
- Session recorded with `session_type = "weak_area_drill"` for separate tracking

---

## 5. Daily Digest Command

**Command:** `codepractice digest`

Non-TUI Rich output: streak status, today's plan theme, review queue size,
and one short LLM-generated motivational tip based on recent performance.
Fast, scriptable, `.bashrc`-friendly.

**Implementation notes:**
- New Typer subcommand in `main.py`
- Pulls stats from `SessionRepository.get_stats()`, active plan from
  `LearningPlanRepository.get_active()`, review count from `get_review_stats()`
- Single LLM call via `ChatService` with a short "morning briefing" prompt
  that includes streak, weak areas, and today's plan theme
- Falls back gracefully if LLM is offline (prints stats without the tip)
- Rich Panel layout: stats on left, tip on right

---

## 6. Progress Markdown Export

**Command:** `codepractice export --format md`

Extends the existing JSON exporter to render a human-readable progress report
suitable for a dev journal, README, or LinkedIn post.

**Implementation notes:**
- New `--format` flag on the existing `export` Typer command (default: `json`)
- Renders using Rich's `Markdown` or plain string building:
  - 30-day streak chart (reuse existing activity data)
  - Category mastery table (solved / attempted / avg score per category)
  - Top 5 solved problems with scores
  - Active plan progress
  - Spaced repetition queue summary
- Output to file: `~/.codepractice/exports/report_YYYY-MM-DD.md`

---

## 7. Code Diff View After Evaluation

**Location:** Feedback phase of the practice screen

After AI evaluation streams, if the response contains an `optimized_solution`
code block, render a before/after comparison using Rich `Columns`.

**Implementation notes:**
- The evaluator prompt already requests `optimized_solution` in its JSON —
  parse it out in `_evaluate_code()` using the existing `extract_json()` helper
- If present, append a "Suggested Approach" panel below the feedback stream
  using `StreamingOutput.write_line()` with syntax-highlighted code via
  Rich `Syntax`
- Only show if user's score < 0.9 (no need to show diff on near-perfect solves)
- No new LLM calls; pure rendering improvement

---

## 8. Per-Problem Personal Difficulty Rating

**Location:** Feedback phase — appears after evaluation completes

A 1–5 prompt: "How hard did *you* find this?" Stored alongside the AI score.
Over time, surfaces problems where perceived difficulty diverges from the label.

**Implementation notes:**
- Migration: `ALTER TABLE problem_attempts ADD COLUMN user_difficulty_rating
  INTEGER DEFAULT NULL`
- `SessionRepository.set_difficulty_rating(attempt_id, rating)`
- Post-feedback, show 5 styled `Button` widgets (⬡ × 5) in the action bar;
  selecting one records the rating and enables the "Next Problem" button
- Progress screen gains a "Mislabeled problems" section: problems where
  `AVG(user_difficulty_rating)` is 2+ steps away from the stored difficulty
- Rating is optional — "Skip" button dismisses without recording

---

## 9. Freeform Question Generation from Job Description or Resume Project

**Location:** Job Description screen and Resume Drill screen

Instead of only generating LeetCode-style coding problems, generate **freeform
interview questions** — behavioural, system design, conceptual, and situational
— drawn directly from the job description or a specific resume project.

**Use cases:**
- "Given this JD, what system design questions might they ask me?"
- "I built a Redis-backed rate limiter on my resume — what follow-up questions
  should I be ready for?"
- Generates questions across types: technical deep-dives, trade-off discussions,
  failure/learning stories, architecture decisions

**Implementation notes:**
- New prompt in `llm/prompts/problem_gen.py`: `freeform_questions_prompt(source,
  text, question_types, count)` where `question_types` is a list like
  `["system_design", "behavioural", "conceptual"]`
- New service method: `ProblemGeneratorService.generate_freeform_questions()`
  returns a list of `{"question": str, "type": str, "follow_ups": [str]}`
- New tab/toggle on the Job Description and Resume Drill screens:
  "Coding Problems" vs "Interview Questions"
- Questions displayed in a `DataTable`; clicking one opens a `ModalScreen`
  with the question, follow-ups, and a `TextArea` for the user to draft
  their answer
- Draft answers saved to a new `question_drafts` table
  (question_hash, source_type, draft_text, updated_at)
- Optional: LLM rates the draft answer with brief feedback (same evaluator
  pattern as code evaluation)
