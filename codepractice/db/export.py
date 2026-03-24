"""JSON and Markdown export for all user data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from codepractice.config import EXPORTS_DIR
from codepractice.db.database import DatabaseManager


def export_all(db: DatabaseManager) -> Path:
    """Export all user data to a timestamped JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = EXPORTS_DIR / f"codepractice_export_{timestamp}.json"

    data: dict = {}

    with db.get_connection() as conn:
        # Profile
        row = conn.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
        data["profile"] = dict(row) if row else {}

        # Problems (AI-generated only, not static seeds)
        rows = conn.execute(
            "SELECT * FROM problems WHERE source != 'static'"
        ).fetchall()
        data["problems"] = [dict(r) for r in rows]

        # All sessions and attempts
        sessions = conn.execute("SELECT * FROM practice_sessions ORDER BY started_at").fetchall()
        data["sessions"] = []
        for session in sessions:
            s = dict(session)
            attempts = conn.execute(
                "SELECT * FROM problem_attempts WHERE session_id = ?", (s["id"],)
            ).fetchall()
            s["attempts"] = [dict(a) for a in attempts]
            data["sessions"].append(s)

        # Learning plans
        plans = conn.execute("SELECT * FROM learning_plans ORDER BY created_at").fetchall()
        data["learning_plans"] = []
        for plan in plans:
            p = dict(plan)
            days = conn.execute(
                "SELECT * FROM plan_days WHERE plan_id = ? ORDER BY day_number", (p["id"],)
            ).fetchall()
            p["days"] = [dict(d) for d in days]
            data["learning_plans"].append(p)

        # Chat history
        rows = conn.execute("SELECT * FROM chat_messages ORDER BY created_at").fetchall()
        data["chat_history"] = [dict(r) for r in rows]

        # Progress snapshots
        rows = conn.execute("SELECT * FROM progress_snapshots ORDER BY snapshot_date").fetchall()
        data["progress_snapshots"] = [dict(r) for r in rows]

    data["exported_at"] = datetime.now().isoformat()
    data["version"] = "0.1.0"

    output_path.write_text(json.dumps(data, indent=2, default=str))
    return output_path


def export_markdown(db: DatabaseManager, output_dir: Path | None = None) -> Path:
    """Export a human-readable progress report as Markdown."""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    out_dir = output_dir or EXPORTS_DIR
    output_path = out_dir / f"report_{timestamp}.md"

    lines: list[str] = []

    with db.get_connection() as conn:
        # ── Stats ─────────────────────────────────────────────────────────────
        total_row = conn.execute(
            "SELECT COUNT(*) AS cnt, AVG(ai_score) AS avg FROM problem_attempts"
        ).fetchone()
        solved_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM problem_attempts WHERE passed = 1"
        ).fetchone()
        streak_row = conn.execute(
            """SELECT COUNT(DISTINCT DATE(attempted_at)) AS days
               FROM problem_attempts
               WHERE attempted_at >= DATE('now', '-30 days')"""
        ).fetchone()
        today_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM problem_attempts WHERE DATE(attempted_at) = DATE('now')"
        ).fetchone()

        total_attempts = total_row["cnt"] if total_row else 0
        total_solved = solved_row["cnt"] if solved_row else 0
        avg_score = round((total_row["avg"] or 0) * 100, 1) if total_row else 0.0
        active_days = streak_row["days"] if streak_row else 0
        today_solved = today_row["cnt"] if today_row else 0

        lines += [
            "# CodePractice — Progress Report",
            f"\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n",
            "## Summary Stats\n",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Attempts | {total_attempts} |",
            f"| Total Solved | {total_solved} |",
            f"| Average Score | {avg_score}% |",
            f"| Active Days (30d) | {active_days} |",
            f"| Solved Today | {today_solved} |",
            "",
        ]

        # ── Category mastery table ─────────────────────────────────────────────
        category_rows = conn.execute(
            """SELECT p.category, p.subcategory,
                      COUNT(*) AS attempts,
                      SUM(pa.passed) AS solved,
                      AVG(pa.ai_score) AS avg_score
               FROM problem_attempts pa
               JOIN problems p ON pa.problem_id = p.id
               GROUP BY p.category, p.subcategory
               ORDER BY avg_score DESC"""
        ).fetchall()

        if category_rows:
            lines += [
                "## Category Mastery\n",
                "| Category | Topic | Attempts | Solved | Avg Score |",
                "|----------|-------|----------|--------|-----------|",
            ]
            for r in category_rows:
                avg = round((r["avg_score"] or 0) * 100, 1)
                lines.append(
                    f"| {r['category']} | {r['subcategory'] or '—'} | "
                    f"{r['attempts']} | {r['solved']} | {avg}% |"
                )
            lines.append("")

        # ── Top 5 solved problems ──────────────────────────────────────────────
        top_rows = conn.execute(
            """SELECT p.title, p.difficulty, pa.ai_score
               FROM problem_attempts pa
               JOIN problems p ON pa.problem_id = p.id
               WHERE pa.passed = 1
               ORDER BY pa.ai_score DESC
               LIMIT 5"""
        ).fetchall()

        if top_rows:
            lines += [
                "## Top Solved Problems\n",
                "| Title | Difficulty | Score |",
                "|-------|------------|-------|",
            ]
            for r in top_rows:
                score_pct = round((r["ai_score"] or 0) * 100, 1)
                lines.append(f"| {r['title']} | {r['difficulty']} | {score_pct}% |")
            lines.append("")

        # ── Active learning plan ───────────────────────────────────────────────
        plan_row = conn.execute(
            "SELECT title, current_day, duration_days, status FROM learning_plans WHERE status = 'active' LIMIT 1"
        ).fetchone()
        if plan_row:
            progress_pct = round(plan_row["current_day"] / max(plan_row["duration_days"], 1) * 100)
            lines += [
                "## Active Learning Plan\n",
                f"**{plan_row['title']}**  ",
                f"Day {plan_row['current_day']} / {plan_row['duration_days']} ({progress_pct}% complete)\n",
            ]

        # ── Spaced repetition queue ────────────────────────────────────────────
        try:
            from codepractice.core.spaced_repetition import get_review_stats
            review = get_review_stats(db)
            lines += [
                "## Spaced Repetition\n",
                f"- Due today: **{review.get('due_today', 0)}**",
                f"- Due this week: {review.get('due_this_week', 0)}",
                f"- Total scheduled: {review.get('total_scheduled', 0)}",
                "",
            ]
        except Exception:
            lines += ["## Spaced Repetition\n", "_No review data yet._\n"]

    output_path.write_text("\n".join(lines))
    return output_path
