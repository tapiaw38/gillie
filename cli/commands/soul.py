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
    load_soul,
    save_soul,
    config_exists,
    get_soul_path,
)
from cli.config.schema import SoulConfig

console = Console()

app = typer.Typer(help="Manage the assistant soul (identity + profile).")


def _require_config():
    if not config_exists():
        console.print("[red]✗[/red] No config found. Run [bold cyan]./gillie init[/bold cyan] first.")
        raise typer.Exit(1)


@app.command("show")
def show():
    """Show the current soul (user_id + profile)."""
    _require_config()
    soul = load_soul()
    p = soul.profile

    table = Table(
        title="✨🐟 Soul",
        box=box.ROUNDED,
        border_style="cyan",
        caption=str(get_soul_path()),
    )
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("User ID", soul.user_id)
    table.add_row("Assistant Name", p.assistant_name)
    table.add_row("Business Name", p.business_name)
    table.add_row("Business Context", p.business_context or "[dim]not set[/dim]")
    table.add_row("Functions", p.functions or "[dim]not set[/dim]")
    table.add_row("Role", p.role)

    console.print()
    console.print(table)
    console.print()


@app.command("edit")
def edit():
    """Edit the soul interactively (profile fields + optional ID regeneration)."""
    _require_config()
    config = load_config()
    p = config.profile

    console.print()
    console.print(Panel(
        "✨🐟 [bold]Edit Soul[/bold] — press Enter to keep current value",
        border_style="cyan",
    ))
    console.print()

    assistant_name = inquirer.text(
        message="Assistant name",
        default=p.assistant_name,
    ).execute()

    business_name = inquirer.text(
        message="Business name",
        default=p.business_name,
    ).execute()

    business_context = inquirer.text(
        message="Business context",
        default=p.business_context,
    ).execute()

    functions = inquirer.text(
        message="Functions / tools",
        default=p.functions,
    ).execute()

    regen = inquirer.confirm(
        message=f"Regenerate User ID? (current: {config.user_id})",
        default=False,
    ).execute()

    config.profile.assistant_name = assistant_name or p.assistant_name
    config.profile.business_name = business_name or p.business_name
    config.profile.business_context = business_context
    config.profile.functions = functions

    if regen:
        new_id = str(uuid.uuid4())
        config.user_id = new_id
        console.print(f"  [yellow]New User ID:[/yellow] {new_id}")

    save_config(config)
    console.print()
    console.print("✨🐟 [green]✓[/green] Soul updated.")
    console.print()


@app.command("reset-id")
def reset_id():
    """Regenerate the User ID (creates a new UUID)."""
    _require_config()
    soul = load_soul()
    old_id = soul.user_id

    console.print()
    console.print(f"[yellow]Current User ID:[/yellow] {old_id}")
    confirmed = inquirer.confirm(
        message="Generate a new User ID? This will change the assistant's identity.",
        default=False,
    ).execute()

    if not confirmed:
        console.print("[dim]Cancelled.[/dim]")
        raise typer.Exit(0)

    soul.user_id = str(uuid.uuid4())
    save_soul(soul)
    console.print()
    console.print(f"✨🐟 [green]✓[/green] New User ID: [bold]{soul.user_id}[/bold]")
    console.print()
