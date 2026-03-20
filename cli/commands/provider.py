"""
gillie provider — manage the active AI provider.

Subcommands:
  list    Show all available providers with status
  use     Switch to a provider (updates ~/.gillie/config.json)
  status  Show the current provider and model
"""
import subprocess
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from src.core.platform.config.service import _PROVIDER_PRESETS

app = typer.Typer(help="Manage AI provider (DeepSeek, OpenRouter, Anthropic, OpenAI, etc.)")
console = Console()


def _restart_service_if_running() -> None:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "--quiet", "gillie"],
        capture_output=True,
    )
    if result.returncode == 0:
        console.print("[dim]Restarting gillie service...[/dim]")
        subprocess.run(["systemctl", "--user", "restart", "gillie"])


@app.command("list")
def provider_list():
    """Show all available providers."""
    from cli.config.manager import config_exists, load_config

    current_api_key = ""
    current_base_url = ""
    if config_exists():
        try:
            cfg = load_config()
            current_api_key = cfg.services.openai.api_key
            current_base_url = cfg.services.openai.base_url
        except Exception:
            pass

    table = Table(box=box.ROUNDED, border_style="cyan", show_lines=False)
    table.add_column("Provider", style="bold")
    table.add_column("Base URL", style="dim")
    table.add_column("Default Model")
    table.add_column("Status")

    for name, preset in _PROVIDER_PRESETS.items():
        has_creds = bool(current_api_key)
        status = "[green]credentials found[/green]" if has_creds else "[yellow]no credentials[/yellow]"
        active_marker = ""
        if current_base_url and current_base_url == preset["base_url"]:
            active_marker = " [bold cyan]*[/bold cyan]"
        table.add_row(
            f"{name}{active_marker}",
            preset["base_url"],
            preset["model"],
            status,
        )

    console.print()
    console.print(table)
    console.print()
    console.print("[dim]* = currently configured[/dim]")
    console.print()


@app.command("use")
def provider_use(
    provider: str = typer.Argument(..., help="Provider name (deepseek, openrouter, anthropic, openai)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key (skips interactive prompt)"),
):
    """Switch to a provider and update the configuration."""
    from cli.config.manager import config_exists, load_config, save_config

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    if provider not in _PROVIDER_PRESETS:
        valid = ", ".join(_PROVIDER_PRESETS.keys())
        console.print(f"[red]Unknown provider:[/red] {provider}")
        console.print(f"[dim]Valid providers: {valid}[/dim]")
        raise typer.Exit(1)

    preset = _PROVIDER_PRESETS[provider]

    if api_key:
        resolved_key = api_key
    else:
        resolved_key = typer.prompt(f"Enter API key for {provider}", hide_input=True)

    if not resolved_key:
        console.print("[red]API key cannot be empty.[/red]")
        raise typer.Exit(1)

    cfg = load_config()
    cfg.services.openai.api_key = resolved_key
    cfg.services.openai.base_url = preset["base_url"]
    cfg.services.openai.model = preset["model"]
    cfg.services.openai.auth_type = preset["auth_type"]
    save_config(cfg)

    console.print(f"[green]Provider switched to[/green] [bold cyan]{provider}[/bold cyan]")
    console.print(f"  Base URL : {preset['base_url']}")
    console.print(f"  Model    : {preset['model']}")
    console.print()

    _restart_service_if_running()


@app.command("status")
def provider_status():
    """Show the current provider configuration."""
    from cli.config.manager import config_exists, load_config

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    cfg = load_config()
    s = cfg.services.openai

    active_provider = next(
        (name for name, p in _PROVIDER_PRESETS.items() if p["base_url"] == s.base_url),
        "custom",
    )

    console.print()
    console.print(f"[bold]Provider :[/bold] [cyan]{active_provider}[/cyan]")
    console.print(f"[bold]Base URL :[/bold] {s.base_url}")
    console.print(f"[bold]Model    :[/bold] {s.model}")
    key_status = "[green]present[/green]" if s.api_key else "[red]missing[/red]"
    console.print(f"[bold]API key  :[/bold] {key_status}")
    console.print()
