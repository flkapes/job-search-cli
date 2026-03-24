"""CLI entry point — Typer commands for launching the TUI and utilities."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="codepractice",
    help="AI-Powered Coding Practice Platform",
    no_args_is_help=False,
    add_completion=False,
)
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Launch the CodePractice TUI."""
    if ctx.invoked_subcommand is None:
        _check_first_run()
        from codepractice.tui.app import run_app
        run_app()


@app.command()
def start():
    """Launch the interactive TUI."""
    _check_first_run()
    from codepractice.tui.app import run_app
    run_app()


@app.command()
def stats():
    """Show quick stats summary (no TUI)."""
    from codepractice.db import get_db
    from codepractice.db.repositories import SessionRepository

    db = get_db()
    repo = SessionRepository(db)
    s = repo.get_stats()

    table = Table(title="Your Progress", border_style="blue")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")
    table.add_row("Today's Problems", str(s["today_solved"]))
    table.add_row("Total Solved", str(s["total_solved"]))
    table.add_row("Average Score", f"{s['avg_score']:.1f}%")
    table.add_row("Active Days (30d)", str(s["active_days_30"]))
    table.add_row("Total Attempts", str(s["total_attempts"]))
    console.print(table)


@app.command()
def export(
    format: str = typer.Option("json", "--format", "-f", help="Output format: json or md"),
):
    """Export all data to JSON or a Markdown progress report."""
    from codepractice.db import get_db

    db = get_db()

    if format.lower() == "md":
        from codepractice.db.export import export_markdown
        path = export_markdown(db)
        console.print(f"[green]✓[/green] Markdown report exported to: [bold]{path}[/bold]")
    else:
        from codepractice.db.export import export_all
        path = export_all(db)
        console.print(f"[green]✓[/green] Data exported to: [bold]{path}[/bold]")


@app.command()
def config():
    """Configure LLM backend and profile."""
    _run_setup_wizard(force=True)


@app.command()
def check():
    """Check LLM connection status."""
    from codepractice.llm.client import get_client

    client = get_client()
    console.print(f"Backend: [bold]{client.__class__.__name__}[/bold]")

    if client.health_check():
        console.print("[green]✓ Connected![/green]")
        models = client.list_models()
        if models:
            console.print(f"Available models: {', '.join(models[:10])}")
    else:
        console.print("[red]✗ Cannot connect to LLM backend[/red]")
        console.print("Make sure Ollama or LM Studio is running.")


@app.command()
def prefetch(
    count: int = typer.Option(10, "--count", "-n", help="Number of problems to generate"),
    category: str = typer.Option("", "--category", help="Category: dsa or python_fundamentals"),
    difficulty: str = typer.Option("", "--difficulty", help="Difficulty: easy, medium, or hard"),
):
    """Pre-generate and cache problems so practice works when the LLM is cold."""
    from codepractice.config import DSA_PATTERNS
    from codepractice.db import get_db
    from codepractice.db.repositories import ProblemRepository
    from codepractice.llm.client import get_client
    from codepractice.llm.services.problem_generator import ProblemGeneratorService

    db = get_db()
    repo = ProblemRepository(db)
    client = get_client()
    svc = ProblemGeneratorService(client)

    patterns = [p["id"] for p in DSA_PATTERNS]
    python_subtopics = ["vocabulary", "builtins", "oop", "threading", "patterns"]
    difficulties = ["easy", "medium", "hard"]

    saved = 0
    failed = 0

    console.print(f"[bold blue]Generating {count} problems...[/bold blue]")

    for i in range(count):
        diff = difficulty or difficulties[i % len(difficulties)]
        problem = None

        if category == "python_fundamentals":
            subtopic = python_subtopics[i % len(python_subtopics)]
            problem = svc.generate_python_fundamental(
                subtopic.replace("_", " ").title(), subtopic, diff
            )
        else:
            # default: dsa
            pattern = patterns[i % len(patterns)]
            problem = svc.generate_dsa(pattern, diff)

        if problem:
            try:
                repo.create({
                    "source": "ai_generated",
                    "category": problem.category,
                    "subcategory": problem.subcategory,
                    "difficulty": (
                        problem.difficulty.value
                        if hasattr(problem.difficulty, "value")
                        else str(problem.difficulty)
                    ),
                    "title": problem.title,
                    "description": problem.description,
                    "constraints": problem.constraints,
                    "examples": [e.model_dump() for e in problem.examples],
                    "hints": problem.hints,
                    "solution": problem.solution.model_dump() if problem.solution else None,
                    "tags": problem.tags,
                })
                saved += 1
                console.print(f"  [green]✓[/green] [{saved}/{count}] {problem.title}")
            except Exception as exc:
                failed += 1
                console.print(f"  [yellow]⚠[/yellow] Failed to save: {exc}")
        else:
            failed += 1

    console.print(f"\n[green]✓[/green] Cached {saved} problem{'s' if saved != 1 else ''}.")
    if failed:
        console.print(
            f"[yellow]⚠[/yellow] {failed} problem{'s' if failed != 1 else ''} failed "
            "(LLM unavailable or returned invalid JSON)."
        )


@app.command()
def digest():
    """Show a daily progress digest: stats, review queue, and an AI tip."""
    from codepractice.db import get_db
    from codepractice.db.repositories import LearningPlanRepository, SessionRepository

    db = get_db()
    sess_repo = SessionRepository(db)
    plan_repo = LearningPlanRepository(db)

    stats = sess_repo.get_stats()

    # Spaced repetition
    try:
        from codepractice.core.spaced_repetition import get_review_stats
        review = get_review_stats(db)
    except Exception:
        review = {"due_today": 0, "due_this_week": 0, "total_scheduled": 0}

    # Active plan
    active_plan = plan_repo.get_active()
    plan_info = ""
    if active_plan:
        plan_info = (
            f"[bold]Active Plan:[/bold] {active_plan.get('title', 'Unnamed')}  "
            f"Day {active_plan.get('current_day', 1)}/{active_plan.get('duration_days', 30)}"
        )

    # Stats table
    table = Table(title="📅 Daily Digest", border_style="blue", show_header=True)
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")
    table.add_row("Solved Today", str(stats.get("today_solved", 0)))
    table.add_row("Total Solved", str(stats.get("total_solved", 0)))
    table.add_row("Avg Score", f"{stats.get('avg_score', 0):.1f}%")
    table.add_row("Active Days (30d)", str(stats.get("active_days_30", 0)))
    table.add_row("Due for Review", str(review.get("due_today", 0)))
    table.add_row("Due This Week", str(review.get("due_this_week", 0)))
    console.print(table)

    if plan_info:
        console.print(f"\n{plan_info}")

    # LLM motivational tip (optional — falls back gracefully)
    try:
        from codepractice.llm.client import get_client

        client = get_client()
        if client.health_check():
            category_scores = sess_repo.get_category_scores()
            from codepractice.core.difficulty import get_weak_areas
            weak = get_weak_areas(category_scores)
            weak_str = ", ".join(weak) if weak else "none identified yet"

            from codepractice.llm.prompts.base import system_message, user_message
            msgs = [
                system_message(),
                user_message(
                    f"Give a short (2-3 sentence) motivational tip for a developer who:\n"
                    f"- Has solved {stats.get('total_solved', 0)} problems total\n"
                    f"- Scored an average of {stats.get('avg_score', 0):.1f}%\n"
                    f"- Weak areas: {weak_str}\n"
                    f"- Has {review.get('due_today', 0)} problems due for spaced repetition review\n"
                    f"Be encouraging but specific. No generic platitudes."
                ),
            ]
            tip = client.chat_sync(msgs, temperature=0.7)
            if tip:
                console.print(
                    Panel(tip.strip(), title="[bold yellow]💡 Today's Tip[/bold yellow]", border_style="yellow")
                )
    except Exception:
        pass  # LLM offline — digest still works


def _check_first_run() -> None:
    """Run setup wizard on first launch."""
    from codepractice.db import get_db
    from codepractice.db.repositories import ProfileRepository

    db = get_db()
    profile_repo = ProfileRepository(db)
    if not profile_repo.exists():
        _run_setup_wizard()


def _run_setup_wizard(force: bool = False) -> None:
    """Interactive first-run setup wizard using questionary."""
    try:
        import questionary
    except ImportError:
        console.print("[yellow]questionary not installed — skipping setup wizard[/yellow]")
        # Create minimal profile
        from codepractice.db import get_db
        from codepractice.db.repositories import ProfileRepository
        db = get_db()
        ProfileRepository(db).create({"name": "Coder", "experience_level": "mid"})
        return

    console.print(
        Panel(
            "[bold #58a6ff]Welcome to CodePractice![/bold #58a6ff]\n\n"
            "Let's set up your profile and LLM connection.\n"
            "This takes about 30 seconds.",
            border_style="blue",
        )
    )

    name = questionary.text("What's your name?", default="Coder").ask()
    if name is None:
        return

    level = questionary.select(
        "Experience level?",
        choices=["junior", "mid", "senior"],
        default="mid",
    ).ask()

    role = questionary.text(
        "Target role? (optional)",
        default="",
    ).ask()

    backend = questionary.select(
        "LLM Backend?",
        choices=["ollama", "lmstudio"],
        default="ollama",
    ).ask()

    model = "llama3"
    base_url = ""

    if backend == "ollama":
        base_url = questionary.text(
            "Ollama URL?", default="http://localhost:11434"
        ).ask() or "http://localhost:11434"
        # Try to list models
        try:
            from codepractice.llm.client import OllamaClient
            client = OllamaClient(base_url=base_url)
            models = client.list_models()
            if models:
                model = questionary.select("Select model:", choices=models).ask() or "llama3"
            else:
                model = questionary.text("Model name?", default="llama3").ask() or "llama3"
        except Exception:
            model = questionary.text("Model name?", default="llama3").ask() or "llama3"
    else:
        base_url = questionary.text(
            "LM Studio URL?", default="http://localhost:1234/v1"
        ).ask() or "http://localhost:1234/v1"
        model = questionary.text("Model name?", default="local-model").ask() or "local-model"

    # Save profile
    from codepractice.db import get_db
    from codepractice.db.repositories import ProfileRepository

    db = get_db()
    repo = ProfileRepository(db)
    repo.create({
        "name": name,
        "experience_level": level,
        "target_role": role or "",
        "llm_backend": backend,
        "llm_model": model,
        "llm_base_url": base_url,
    })

    console.print(f"\n[green]✓[/green] Profile saved! Welcome, [bold]{name}[/bold].")
    console.print(f"  Backend: {backend} ({model})")
    console.print("  Run [bold]codepractice[/bold] to launch the TUI.\n")


# Allow running as module
if __name__ == "__main__":
    app()
