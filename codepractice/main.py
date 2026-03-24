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
def export():
    """Export all data to JSON."""
    from codepractice.db import get_db
    from codepractice.db.export import export_all

    db = get_db()
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
