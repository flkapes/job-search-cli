# Next Sprint — Implementation Queue

Features queued for implementation, in priority order.

> **Where things live:** [`ROADMAP.md`](ROADMAP.md) is the long-range plan,
> this file is the actionable queue, [`CHANGELOG.md`](CHANGELOG.md) records
> what has shipped, and [`README.md`](README.md) documents current
> capabilities.

---

## 1. Full Sandbox Isolation

**Location:** `codepractice/utils/sandbox.py` + `code_runner.py`

Resource limits (CPU, memory, file size) shipped in 0.2.0; true isolation
is still open.

- No-network execution for submitted code
- Restricted filesystem visibility (namespaces/seccomp on Linux,
  `sandbox-exec` on macOS)
- Required before promoting shared problem imports beyond
  trusted sources

## 2. AI Mock Interviewer

**Location:** chat service + interview simulation mode

A conversational interviewer persona wrapped around the existing practice
loop — the product's flagship differentiator.

- Presents the problem verbally and answers clarifying questions
- Probes follow-ups: time complexity, space optimization, edge cases
- Post-session transcript with rubric scoring (communication, correctness,
  optimization, testing instincts)

## 3. Vim / Emacs Keybindings

**Location:** code editor + profile settings

- Standard / Vim / Emacs mode toggle in Settings, persisted per profile
- `i`/`Esc` modal editing in Vim mode; core Emacs chords in Emacs mode

---

For everything already shipped — including the 2026-07-08 sprint
(verified test cases, gamification, bookmarks, cloud backends, company
profiles, custom problems, multi-language practice, flicker-free
streaming) — see [`CHANGELOG.md`](CHANGELOG.md).
