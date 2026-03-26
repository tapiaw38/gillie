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
vision_app = typer.Typer(help="Configure vision AI provider for image description")
app.add_typer(vision_app, name="vision")
console = Console()

_VISION_PRESETS: dict = {
    "deepseek": {"base_url": "https://api.deepseek.com",                                "model": "deepseek-vl2"},
    "gemini":   {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-2.0-flash"},
    "groq":     {"base_url": "https://api.groq.com/openai/v1",                          "model": "meta-llama/llama-4-scout-17b-16e-instruct"},
    "openai":   {"base_url": "https://api.openai.com/v1",                               "model": "gpt-4o"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1",                          "model": "google/gemini-2.0-flash-exp:free"},
}


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

    from pathlib import Path as _Path
    _has_claude_session = (_Path.home() / ".claude" / ".credentials.json").exists()

    for name, preset in _PROVIDER_PRESETS.items():
        if preset.get("auth_type") == "bearer":
            status = "[green]session found[/green]" if _has_claude_session else "[yellow]no session[/yellow]"
        else:
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
    provider: str = typer.Argument(..., help="Provider name (deepseek, openrouter, anthropic, openai, claude, kimi, gemini, groq)"),
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

    if preset.get("auth_type") == "bearer":
        # Bearer providers use a local OAuth token instead of an API key.
        # Read it from ~/.claude/.credentials.json (Claude Code session).
        import json
        from pathlib import Path
        creds_path = Path.home() / ".claude" / ".credentials.json"
        if creds_path.exists():
            try:
                creds = json.loads(creds_path.read_text())
                resolved_key = creds.get("claudeAiOauth", {}).get("accessToken", "")
            except Exception:
                resolved_key = ""
        else:
            resolved_key = ""

        if not resolved_key:
            console.print("[yellow]Could not read Claude Code session from ~/.claude/.credentials.json[/yellow]")
            console.print("[dim]Make sure you are logged in to Claude Code (claude.ai/code)[/dim]")
            if api_key:
                resolved_key = api_key
            else:
                console.print("[red]No bearer token available.[/red]")
                raise typer.Exit(1)
        else:
            console.print("[dim]Using Claude Code session token from ~/.claude/.credentials.json[/dim]")
    elif api_key:
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


# ── Vision subcommands ────────────────────────────────────────────────────────

@vision_app.command("set")
def vision_set(
    provider: Optional[str] = typer.Argument(None, help="Preset provider (gemini, groq, openai, openrouter)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL (overrides preset)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name (overrides preset)"),
):
    """Set the vision provider used for image description."""
    from cli.config.manager import config_exists, load_config, save_config

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    preset = _VISION_PRESETS.get(provider, {}) if provider else {}

    if not preset and provider and provider not in _VISION_PRESETS:
        valid = ", ".join(_VISION_PRESETS.keys())
        console.print(f"[red]Unknown preset:[/red] {provider}")
        console.print(f"[dim]Known presets: {valid}[/dim]")
        console.print("[dim]Or omit the provider and use --base-url and --model directly.[/dim]")
        raise typer.Exit(1)

    resolved_key = api_key or typer.prompt("Enter vision API key", hide_input=True)
    if not resolved_key:
        console.print("[red]API key cannot be empty.[/red]")
        raise typer.Exit(1)

    resolved_base_url = base_url or preset.get("base_url", "")
    resolved_model = model or preset.get("model", "")

    if not resolved_base_url:
        resolved_base_url = typer.prompt("Base URL")
    if not resolved_model:
        resolved_model = typer.prompt("Model name")

    cfg = load_config()
    cfg.services.vision.api_key = resolved_key
    cfg.services.vision.base_url = resolved_base_url
    cfg.services.vision.model = resolved_model
    save_config(cfg)

    label = provider or "custom"
    console.print(f"\n[green]Vision provider set:[/green] [bold cyan]{label}[/bold cyan]")
    console.print(f"  Base URL : {resolved_base_url}")
    console.print(f"  Model    : {resolved_model}")
    console.print()
    _restart_service_if_running()


@vision_app.command("status")
def vision_status():
    """Show the current vision provider configuration."""
    from cli.config.manager import config_exists, load_config

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    cfg = load_config()
    v = cfg.services.vision

    active = next(
        (name for name, p in _VISION_PRESETS.items() if p["base_url"] == v.base_url),
        "custom" if v.base_url else "not configured",
    )

    console.print()
    console.print(f"[bold]Provider :[/bold] [cyan]{active}[/cyan]")
    console.print(f"[bold]Base URL :[/bold] {v.base_url or '[dim]—[/dim]'}")
    console.print(f"[bold]Model    :[/bold] {v.model or '[dim]—[/dim]'}")
    key_status = "[green]present[/green]" if v.api_key else "[red]missing[/red]"
    console.print(f"[bold]API key  :[/bold] {key_status}")
    console.print()


@vision_app.command("clear")
def vision_clear():
    """Remove the vision provider configuration (falls back to technical analysis)."""
    from cli.config.manager import config_exists, load_config, save_config

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    cfg = load_config()
    cfg.services.vision.api_key = ""
    cfg.services.vision.base_url = ""
    cfg.services.vision.model = ""
    save_config(cfg)

    console.print("[yellow]Vision provider cleared.[/yellow] Falling back to technical analysis.")
    _restart_service_if_running()
