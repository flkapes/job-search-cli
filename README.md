# ⬡ CodePractice

**An adaptive, AI-powered coding practice platform for your terminal.**

[![CI](https://github.com/flkapes/job-search-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/flkapes/job-search-cli/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0-informational.svg)](CHANGELOG.md)

CodePractice is an interactive terminal application for technical interview preparation. Drill Python fundamentals and DSA patterns, practice in **Python, JavaScript, or Go** with verified test cases, and get AI-driven evaluation and coaching — using a local LLM by default, or a cloud API if you prefer.

```
   ██████╗ ██████╗ ██████╗ ███████╗
  ██╔════╝██╔═══██╗██╔══██╗██╔════╝
  ██║     ██║   ██║██║  ██║█████╗
  ██║     ██║   ██║██║  ██║██╔══╝
  ╚██████╗╚██████╔╝██████╔╝███████╗
   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
         P R A C T I C E
```

[Features](#-features) · [Quick Start](#-quick-start) · [Configuration](#%EF%B8%8F-configuration) · [Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md)

---

## ✨ Features

### 🐍 Python Fundamentals Track
Drill core Python concepts with curated + AI-generated problems:
- **Vocabulary** — comprehensions, generators, decorators, context managers
- **Built-ins** — map, filter, zip, enumerate, functools, itertools
- **OOP** — classes, descriptors, dunder methods, dataclasses, ABCs
- **Threading** — threading.Thread, Lock, concurrent.futures, asyncio
- **Design Patterns** — Observer, Factory, Strategy, Singleton in Python
- **Version Control** — git concepts, branching strategies, merge vs rebase

### 🧩 DSA Pattern Training
Structured drills organized by pattern — the way interviewers think:
- Two Pointers · Sliding Window · Binary Search
- BFS / DFS · Dynamic Programming · Backtracking
- Heap / Priority Queue · Prefix Sum · Monotonic Stack · Union Find

### 📄 Resume Drill
Paste your resume → AI analyzes your skills and projects → generates targeted practice that reinforces what's on your resume so you can speak confidently in interviews.

### 💼 Job Description Prep
Paste a job description → AI generates practical coding problems focused on the real-world skills the role requires (not just abstract DSA).

### 📅 Adaptive Learning Plans
Describe your goal in natural language:
> *"Prepare me for a backend Python interview in 14 days"*

The AI creates a structured day-by-day plan that **evolves over time** based on your performance. You can also record goal changes and refresh your active plan from the CLI (`codepractice goal "..."`) or from the Learning Plan screen.

### 💬 AI Coach Chat
Chat with your AI coding coach. It knows your profile, current plan, recent performance, and weak areas. Ask for explanations, code reviews, or motivation.

### 📊 Progress Tracking
- Daily activity charts
- Category mastery heatmaps
- Streak tracking
- Weak area identification
- Session history

### 🧪 Interview Simulation Mode
- Timed interview-style practice sessions from Dashboard (**Interview Sim**)
- DSA problems only, alternating medium and hard — like a real loop
- Countdown timer with color states (green → yellow → red)
- Hints disabled; each peek deducts 5% from the final score
- Early finish action + automatic timeout end
- End-of-session scorecard with attempted/solved, score (with peek penalty), and category breakdown

### ✅ Verified Test Cases
Submissions run against each problem's examples and the actual output is compared to the expected output. The AI refines the score but can't pass code that fails its test cases — and when the LLM is offline, scoring falls back to the real test results.

All **53 bundled problems** — every DSA pattern at every difficulty, three per Python topic, plus a practical set — ship in verifiable input/output format, and every reference solution is machine-checked against its examples in CI. AI-generated problems carry the same guarantee: the generated solution is executed against the generated examples, and problems that fail are rejected instead of saved.

### 🏆 XP, Levels & Achievements
- XP per attempt scaled by difficulty × score, with speed and no-hint bonuses
- 8 level tiers from **Intern** to **Distinguished Engineer**
- 18 achievements (7-Day Streak, Speed Demon, DSA Master, Polyglot, …) with unlock toasts and a gallery on the Progress screen

### 📚 Bookmarks & My Library
Press `B` on any problem to bookmark it. The **My Library** screen lists your bookmarks with filters and opens a side-by-side comparison of your best solution vs the AI-optimal one.

### 🏢 Company Prep Profiles
Browse interview profiles for 10 top companies (patterns, focus areas, round structure, difficulty mix) and generate a targeted learning plan with one click. Known companies also enrich Job Description problem generation.

### ✏️ Custom Problems
Author your own drill problems in the TUI — they join random practice and the review queue — and share them via `codepractice export-problems` / `import-problems`.

### 🌍 Multi-Language Practice
Solve problems in **Python, JavaScript, or Go** (selector appears for installed toolchains). Test-case verification, syntax highlighting, and AI evaluation all adapt to the chosen language.

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| TUI Framework | [Textual](https://textual.textualize.io/) — full interactive terminal app |
| Rich Output | [Rich](https://rich.readthedocs.io/) — panels, tables, syntax highlighting |
| LLM Backend | [Ollama](https://ollama.com/) / [LM Studio](https://lmstudio.ai/) (local, default) · [Anthropic API](https://platform.claude.com/) / OpenAI-compatible (cloud, optional) |
| Data Models | [Pydantic](https://docs.pydantic.dev/) v2 — typed, validated models |
| CLI | [Typer](https://typer.tiangolo.com/) — modern CLI framework |
| Database | SQLite — zero-config persistent storage |
| Code Execution | Subprocess with POSIX resource limits (CPU, memory, file size) |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- An LLM backend — any one of:
  - [Ollama](https://ollama.com/) or [LM Studio](https://lmstudio.ai/) running locally (default, fully private), or
  - an Anthropic or OpenAI-compatible API key (see [Configuration](#%EF%B8%8F-configuration))
- Optional: [Node.js](https://nodejs.org/) and/or [Go](https://go.dev/) to practice in JavaScript or Go

### Install

```bash
# Clone
git clone https://github.com/flkapes/job-search-cli.git
cd job-search-cli

# Install
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

### Launch

```bash
# Interactive TUI (recommended)
codepractice

# Or run as module
python -m codepractice
```

On first launch, a setup wizard helps configure your profile and LLM connection.

### CLI Commands

```bash
codepractice          # Launch the TUI
codepractice start    # Same as above
codepractice stats    # Quick stats (no TUI)
codepractice config   # Re-run setup wizard
codepractice check    # Test LLM connection
codepractice export   # Export all data to JSON
codepractice digest   # Daily digest with stats/review/plan snapshot
codepractice prefetch # Warm local problem cache
codepractice goal "..." # Save a goal update and optionally regenerate active plan
codepractice export-problems [file] # Export your custom problems to JSON
codepractice import-problems <file> # Import shared custom problems
```

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and edit:

```bash
cp .env.example .env
```

```env
# LLM Backend: "ollama" | "lmstudio" (local) | "anthropic" | "openai" (cloud)
LLM_BACKEND=ollama

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# LM Studio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=local-model

# Cloud backends (optional; keys are read from the environment only)
# LLM_BACKEND=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_MODEL=claude-opus-4-8
#
# LLM_BACKEND=openai
# OPENAI_API_KEY=sk-...
# OPENAI_BASE_URL=https://api.openai.com/v1
```

**Recommended local models:** `llama3`, `codellama`, `deepseek-coder`, `mistral`

---

## 🎮 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `d` | Dashboard (Interview Sim lives in its Quick Start row) |
| `p` | Free Practice |
| `r` | Review session (spaced repetition) |
| `t` | Python Track |
| `a` | DSA Training |
| `l` | Learning Plan |
| `c` | AI Coach Chat |
| `s` | Profile & Settings |
| `h` | Show hint (in practice) |
| `n` | Next problem (in practice) |
| `b` | Bookmark problem (in practice) |
| `Ctrl+Enter` | Submit code |
| `q` | Quit |

Screens without a shortcut — **Companies**, **My Library**, **New Problem**, **Resume Drill**, **Job Description**, and **Progress** — are reachable from the sidebar.

---

## 📁 Project Structure

```
codepractice/
├── main.py              # CLI entry point (Typer)
├── config.py            # Configuration, theme palette
├── data/                # Bundled problems + company profiles
├── tui/
│   ├── app.py           # Root Textual app, screen router
│   ├── theme.tcss       # GitHub-dark theme
│   ├── screens/         # Dashboard, Practice, Library, Companies, Chat, …
│   └── widgets/         # Header, Sidebar, CodeEditor, StreamingOutput
├── llm/
│   ├── client.py        # Ollama, LM Studio, Anthropic, OpenAI-compatible
│   ├── prompts/         # Structured prompt templates
│   └── services/        # Problem generation, evaluation, planning
├── db/
│   ├── database.py      # SQLite + auto-migrations
│   ├── migrations/      # Schema versioning
│   └── repositories/    # Data access layer
├── core/
│   ├── models.py        # Pydantic data models
│   ├── difficulty.py    # Adaptive difficulty engine
│   ├── gamification.py  # XP rules, levels, achievements
│   ├── spaced_repetition.py  # Review scheduling
│   ├── company_profiles.py   # Company prep data + plan builder
│   ├── custom_problems.py    # Custom problem authoring + import/export
│   └── problem_bank.py  # Bundled problem loader
└── utils/
    ├── code_runner.py   # Multi-language execution + test verification
    ├── languages.py     # Python / JavaScript / Go runner registry
    ├── sandbox.py       # POSIX resource limits for submitted code
    └── text_utils.py    # Formatting helpers
```

---

## 🗄 Data & Privacy

- All data stored locally in `~/.codepractice/codepractice.db`
- With the default local backends (Ollama / LM Studio), **no data is sent to the cloud**
- The optional `anthropic` / `openai` backends send prompts to the provider's API; API keys live in your `.env` only and are never stored in the database
- Export anytime: `codepractice export` produces a full JSON snapshot

---

## 🤝 Contributing

1. Fork the repo and create a feature branch
2. Install dev dependencies: `pip install -e ".[dev]"`
3. Make your changes, with tests
4. Verify locally — the same checks run in CI:
   ```bash
   ruff check codepractice/
   pytest --cov=codepractice --cov-fail-under=40
   ```
5. Open a pull request

Planned work lives in [ROADMAP.md](ROADMAP.md); the current implementation queue is in [NEXT_SPRINT.md](NEXT_SPRINT.md).

---

## 📄 License

Released under the [MIT License](LICENSE).
