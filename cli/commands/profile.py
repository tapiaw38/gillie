import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from InquirerPy import inquirer

from cli.config.manager import load_config, save_config, config_exists

console = Console()

app = typer.Typer(help="Manage assistant profile configuration.")


def _require_config():
    if not config_exists():
        console.print("[red]✗[/red] No config found. Run [bold cyan]./gillie init[/bold cyan] first.")
        raise typer.Exit(1)


@app.command("show")
def show():
    """Show the current profile configuration."""
    _require_config()
    config = load_config()
    p = config.profile

    table = Table(title="✨🐟 Assistant Profile", box=box.ROUNDED, border_style="cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("User ID", config.user_id)
    table.add_row("Assistant Name", p.assistant_name)
    table.add_row("Business Name", p.business_name or "[dim]not set[/dim]")
    table.add_row("Functions", p.functions or "[dim]not set[/dim]")

    console.print()
    console.print(table)
    console.print()


@app.command("edit")
def edit():
    """Edit the assistant profile configuration interactively."""
    _require_config()
    config = load_config()
    p = config.profile

    console.print()
    console.print(Panel("[bold]Edit Profile[/bold] — press Enter to keep current value", border_style="cyan"))
    console.print()

    assistant_name = inquirer.text(
        message="Assistant name",
        default=p.assistant_name,
    ).execute()

    business_name = inquirer.text(
        message="Business name (optional)",
        default=p.business_name,
    ).execute()

    functions = inquirer.text(
        message="Functions / tools",
        default=p.functions,
    ).execute()

    config.profile.assistant_name = assistant_name or p.assistant_name
    config.profile.business_name = business_name
    config.profile.functions = functions

    save_config(config)
    console.print()
    console.print("✨🐟 [green]✓[/green] Profile updated.")
    console.print()
