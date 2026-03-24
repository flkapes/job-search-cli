"""App-wide configuration, paths, and theme constants."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────

DATA_DIR = Path(os.environ.get("CODEPRACTICE_DATA_DIR", Path.home() / ".codepractice"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "codepractice.db"
EXPORTS_DIR = DATA_DIR / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

# Static problem data bundled with the package
_PACKAGE_DIR = Path(__file__).parent.parent
PROBLEMS_DATA_DIR = _PACKAGE_DIR / "data" / "problems"

# ── LLM Configuration ──────────────────────────────────────────────────────────

LLM_BACKEND = os.environ.get("LLM_BACKEND", "ollama")  # "ollama" | "lmstudio"

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")

LMSTUDIO_BASE_URL = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = os.environ.get("LMSTUDIO_MODEL", "local-model")

LLM_TIMEOUT = 120  # seconds
LLM_MAX_RETRIES = 3

DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# ── App Theme Palette ──────────────────────────────────────────────────────────

THEME = {
    "background": "#0d1117",
    "surface": "#161b22",
    "surface_alt": "#1c2128",
    "border": "#30363d",
    "primary": "#58a6ff",
    "primary_dim": "#1f6feb",
    "success": "#3fb950",
    "warning": "#d29922",
    "danger": "#f85149",
    "text": "#c9d1d9",
    "text_muted": "#8b949e",
    "text_dim": "#484f58",
    "easy": "#3fb950",
    "medium": "#d29922",
    "hard": "#f85149",
    "accent_purple": "#bc8cff",
    "accent_orange": "#e3b341",
}

# ── DSA Pattern Definitions ────────────────────────────────────────────────────

DSA_PATTERNS = [
    {"id": "two_pointers", "name": "Two Pointers", "icon": "↔", "description": "Use two indices moving toward each other or in the same direction."},
    {"id": "sliding_window", "name": "Sliding Window", "icon": "⊡", "description": "Maintain a window of elements to track a subset efficiently."},
    {"id": "binary_search", "name": "Binary Search", "icon": "⌖", "description": "Divide and conquer on sorted data to find targets in O(log n)."},
    {"id": "bfs", "name": "BFS / Level Order", "icon": "⊛", "description": "Breadth-first traversal of graphs and trees."},
    {"id": "dfs", "name": "DFS / Backtracking", "icon": "⬇", "description": "Depth-first exploration with optional state rollback."},
    {"id": "dynamic_programming", "name": "Dynamic Programming", "icon": "▦", "description": "Memoize overlapping subproblems for optimal solutions."},
    {"id": "heap", "name": "Heap / Priority Queue", "icon": "△", "description": "Efficiently track min/max elements in a stream."},
    {"id": "prefix_sum", "name": "Prefix Sum", "icon": "Σ", "description": "Precompute cumulative sums for O(1) range queries."},
    {"id": "monotonic_stack", "name": "Monotonic Stack", "icon": "⊓", "description": "Stack maintaining increasing or decreasing order."},
    {"id": "union_find", "name": "Union Find", "icon": "∪", "description": "Efficiently group and query connected components."},
]

# ── Python Fundamentals Curriculum ────────────────────────────────────────────

PYTHON_TOPICS = [
    {"id": "vocabulary", "name": "Core Vocabulary", "icon": "📖", "description": "Types, keywords, expressions, comprehensions, generators, decorators, context managers."},
    {"id": "builtins", "name": "Built-in Functions", "icon": "🔧", "description": "map, filter, zip, enumerate, sorted, functools, itertools, collections."},
    {"id": "oop", "name": "OOP & Classes", "icon": "🏗", "description": "Classes, inheritance, dunder methods, dataclasses, ABCs, properties, classmethods."},
    {"id": "threading", "name": "Threading & Async", "icon": "⚡", "description": "threading.Thread, Lock, Queue, concurrent.futures, asyncio basics, GIL."},
    {"id": "version_control", "name": "Version Control", "icon": "🌿", "description": "Git fundamentals, branching strategies, merge vs rebase, pull requests, conflict resolution."},
    {"id": "patterns", "name": "Design Patterns", "icon": "♟", "description": "Singleton, Factory, Observer, Strategy, Decorator, Context Manager patterns in Python."},
]

# ── Scoring Weights ────────────────────────────────────────────────────────────

SCORE_WEIGHTS = {
    "correctness": 0.50,
    "efficiency": 0.30,
    "style": 0.20,
}

DIFFICULTY_PROMOTION_THRESHOLD = 0.80   # promote if avg score > this
DIFFICULTY_DEMOTION_THRESHOLD = 0.45    # demote if avg score < this
ADAPTIVE_WINDOW = 5                      # look at last N attempts for adaptation
