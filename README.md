# ⬡ CodePractice

**AI-Powered Adaptive Coding Practice Platform**

A beautiful, interactive terminal application that helps developers master Python, crush DSA patterns, and prepare for technical interviews — powered by your local LLM.

```
   ██████╗ ██████╗ ██████╗ ███████╗
  ██╔════╝██╔═══██╗██╔══██╗██╔════╝
  ██║     ██║   ██║██║  ██║█████╗
  ██║     ██║   ██║██║  ██║██╔══╝
  ╚██████╗╚██████╔╝██████╔╝███████╗
   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
         P R A C T I C E
```

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

The AI creates a structured day-by-day plan that **evolves over time** based on your performance, focusing more on weak areas and advancing past mastered topics.

### 💬 AI Coach Chat
Chat with your AI coding coach. It knows your profile, current plan, recent performance, and weak areas. Ask for explanations, code reviews, or motivation.

### 📊 Progress Tracking
- Daily activity charts
- Category mastery heatmaps
- Streak tracking
- Weak area identification
- Session history

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| TUI Framework | [Textual](https://textual.textualize.io/) — full interactive terminal app |
| Rich Output | [Rich](https://rich.readthedocs.io/) — panels, tables, syntax highlighting |
| LLM Backend | [Ollama](https://ollama.com/) or [LM Studio](https://lmstudio.ai/) — local AI |
| Data Models | [Pydantic](https://docs.pydantic.dev/) v2 — typed, validated models |
| CLI | [Typer](https://typer.tiangolo.com/) — modern CLI framework |
| Database | SQLite — zero-config persistent storage |
| Code Execution | Sandboxed subprocess — safe Python execution |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com/) running locally (or LM Studio)

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
```

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and edit:

```bash
cp .env.example .env
```

```env
# LLM Backend: "ollama" or "lmstudio"
LLM_BACKEND=ollama

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# LM Studio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=local-model
```

**Recommended models:** `llama3`, `codellama`, `deepseek-coder`, `mistral`

---

## 🎮 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `d` | Dashboard |
| `p` | Free Practice |
| `t` | Python Track |
| `a` | DSA Training |
| `l` | Learning Plan |
| `c` | AI Coach Chat |
| `s` | Profile & Settings |
| `h` | Show hint (in practice) |
| `n` | Next problem (in practice) |
| `Ctrl+Enter` | Submit code |
| `q` | Quit |

---

## 📁 Project Structure

```
codepractice/
├── main.py              # CLI entry point (Typer)
├── config.py            # Configuration, theme palette
├── tui/
│   ├── app.py           # Root Textual app, screen router
│   ├── theme.tcss       # Claude-inspired dark theme
│   ├── screens/         # Dashboard, Practice, DSA, Chat, etc.
│   └── widgets/         # Header, Sidebar, CodeEditor, StreamingOutput
├── llm/
│   ├── client.py        # Ollama + LM Studio backends
│   ├── prompts/         # Structured prompt templates
│   └── services/        # Problem generation, evaluation, planning
├── db/
│   ├── database.py      # SQLite + auto-migrations
│   ├── migrations/      # Schema versioning
│   └── repositories/    # Clean data access layer
├── core/
│   ├── models.py        # Pydantic data models
│   ├── difficulty.py    # Adaptive difficulty engine
│   └── problem_bank.py  # Static problem loader
└── utils/
    ├── code_runner.py   # Sandboxed Python execution
    └── text_utils.py    # Formatting helpers
```

---

## 🗄 Data & Privacy

- All data stored locally in `~/.codepractice/codepractice.db`
- LLM runs locally — **no data sent to the cloud**
- Export anytime: `codepractice export` produces a full JSON snapshot

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Install dev deps: `pip install -e ".[dev]"`
4. Run tests: `pytest`
5. Submit a PR

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
