"""JSON export/import for all user data."""

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
