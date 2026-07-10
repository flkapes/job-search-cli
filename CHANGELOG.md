# Changelog

All notable changes to CodePractice are documented here.

## 0.2.0 — 2026-07-08

### Added
- **Verified test cases** — submissions run against problem examples and actual
  output is compared to expected output; deterministic results cap/floor the
  AI score (the LLM can't pass failing code) and drive offline scoring.
- **Gamification** — XP scaled by difficulty × score with speed/no-hint
  bonuses, 8 level tiers, 18 achievements with unlock toasts, and a Level/XP/
  achievements section on the Progress screen.
- **Bookmarks & My Library** — star any problem (`B`), browse bookmarks with
  filters, and compare your best solution side-by-side with the AI-optimal one.
- **Cloud LLM backends** — optional `anthropic` (official SDK) and
  `openai`-compatible backends alongside local Ollama/LM Studio; API keys are
  read from the environment only.
- **Company prep profiles** — 10 curated interview profiles with a searchable
  browser, one-click targeted learning plans (works offline), and Job
  Description enrichment.
- **Custom problems** — author problems in the TUI; share them with
  `codepractice export-problems` / `import-problems`.
- **Multi-language practice** — JavaScript and Go runners with verified test
  cases, per-language highlighting, and per-attempt language tracking.
- **Flicker-free streaming** — LLM tokens are consumed on a worker thread with
  frame-batched writes, a bottom-anchored chat composer, and auto-follow that
  pauses when you scroll up.
- **Interview simulation mode** and **goal evolution tracking** (earlier in
  this cycle).

### Changed
- **AI-generated problems are now self-verifying** — generation prompts
  require runnable stdin/stdout problems, and the generated reference
  solution is executed against the problem's own examples before saving;
  problems that fail are rejected, so everything in the database carries the
  same verification guarantee as the bundled bank.
- **Score guardrails are asymmetric by design** — failing test cases still
  caps the AI score, but passing the two visible examples no longer overrules
  an emphatic AI fail (hard-coding the printed outputs can't force a pass).
- **XP anti-farming** — full XP on a problem's first solve, 25% on repeat
  solves, nothing for failing an already-solved problem.
- **Interview Simulation now behaves like an interview** — problems are
  DSA-only alternating medium/hard, and each hint peek deducts 5% from the
  final scorecard (the penalty was previously recorded but never applied).
- **Version-control problems are scenario questions** — written answers
  reviewed by the AI coach with model answers, replacing echo-a-git-command
  exercises.
- Language selection is offered only on language-agnostic problems (DSA and
  practical); Python-fundamentals problems lock to Python.
- Learning-plan generation uses a 16K token budget so cloud backends don't
  silently truncate long plans into the generic fallback.
- Backend health checks run off the UI thread (no network round-trip during
  app startup); bookmark achievements unlock immediately; company profiles
  carry a last-reviewed date shown in the browser.
- **Problem bank rewritten and expanded** — 53 bundled problems (up from 27),
  covering every DSA pattern at easy/medium/hard, three problems per Python
  topic, and a new practical category. All problems use verifiable
  stdin/stdout examples, and every reference solution is machine-checked
  against its examples in CI, so verified scoring and offline evaluation work
  on all bundled content.

### Fixed
- Test-case execution previously treated any clean exit as a pass.
- LLM-offline evaluation no longer blanket-scores 0.5 when test results exist.
- DSA and Python track drills now honor the selected pattern/topic (they
  previously served random problems from the whole category), and "Next
  problem" keeps the drill's filters.
- "Start Today's Practice" now drills the active plan's task instead of
  opening unfiltered free practice.
- The settings screen offers all four LLM backends (it listed only the local
  ones) and documents where cloud API keys live.
- The offline generation fallback for DSA drills generated Python-fundamentals
  problems.
- Simulation scorecard rendering on the streaming panel.

### Security
- Submitted code now runs with POSIX resource limits (CPU time, address
  space, file size, core dumps) — see `codepractice/utils/sandbox.py`.
  Note: execution is limited, not fully isolated; there is no network or
  filesystem namespace isolation. Review imported problems before running.

## 0.1.0 — 2026-05-22

Initial release: adaptive practice TUI with Python fundamentals and DSA
tracks, resume/JD-driven problem generation, learning plans, AI coach chat,
progress analytics, spaced repetition, session replay, and offline problem
cache.
