import uuid
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from InquirerPy import inquirer

from cli.config.manager import (
    load_config,
    save_config,
    config_exists,
    get_config_path,
)

console = Console()

app = typer.Typer(help="Manage assistant configuration identity and profile.")


def _require_config():
    if not config_exists():
        console.print("[red]✗[/red] No config found. Run [bold cyan]./gillie init[/bold cyan] first.")
        raise typer.Exit(1)


@app.command("show")
def show():
    """Show the current config identity (user_id + profile)."""
    _require_config()
    config = load_config()
    p = config.profile

    table = Table(
        title="✨🐙 Config",
        box=box.ROUNDED,
        border_style="cyan",
        caption=str(get_config_path()),
    )
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("User ID", config.user_id)
    table.add_row("Assistant Name", p.assistant_name)
    table.add_row("Functions", p.functions or "[dim]not set[/dim]")
    table.add_row("Response Language", p.response_language or "en")

    console.print()
    console.print(table)
    console.print()


@app.command("edit")
def edit():
    """Edit config identity fields interactively (profile + optional ID regeneration)."""
    _require_config()
    config = load_config()
    p = config.profile

    console.print()
    console.print(Panel(
        "✨🐙 [bold]Edit Config[/bold] — press Enter to keep current value",
        border_style="cyan",
    ))
    console.print()

    assistant_name = inquirer.text(
        message="Assistant name",
        default=p.assistant_name,
    ).execute()

    functions = inquirer.text(
        message="Functions / tools",
        default=p.functions,
    ).execute()

    response_language = inquirer.select(
        message="Response language",
        choices=["en", "es"],
        default=p.response_language or "en",
    ).execute()

    regen = inquirer.confirm(
        message=f"Regenerate User ID? (current: {config.user_id})",
        default=False,
    ).execute()

    config.profile.assistant_name = assistant_name or p.assistant_name
    config.profile.functions = functions
    config.profile.response_language = response_language

    if regen:
        new_id = str(uuid.uuid4())
        config.user_id = new_id
        console.print(f"  [yellow]New User ID:[/yellow] {new_id}")

    save_config(config)
    console.print()
    console.print("✨🐙 [green]✓[/green] Config updated.")
    console.print()


@app.command("reset-id")
def reset_id():
    """Regenerate the User ID (creates a new UUID)."""
    _require_config()
    config = load_config()
    old_id = config.user_id

    console.print()
    console.print(f"[yellow]Current User ID:[/yellow] {old_id}")
    confirmed = inquirer.confirm(
        message="Generate a new User ID? This will change the assistant's identity.",
        default=False,
    ).execute()

    if not confirmed:
        console.print("[dim]Cancelled.[/dim]")
        raise typer.Exit(0)

    config.user_id = str(uuid.uuid4())
    save_config(config)
    console.print()
    console.print(f"✨🐙 [green]✓[/green] New User ID: [bold]{config.user_id}[/bold]")
    console.print()
