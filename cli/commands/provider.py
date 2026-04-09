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

from src.core.platform.config.service import (
    _PROVIDER_PRESETS,
    get_available_providers,
)
from cli.config.db import update_provider, save_custom_provider, get_provider_data

app = typer.Typer(help="Manage AI provider (DeepSeek, OpenRouter, Anthropic, OpenAI, etc.)")
vision_app = typer.Typer(help="Configure vision AI provider for image description")
app.add_typer(vision_app, name="vision")
console = Console()

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"

def _provider_display_name(name: str, preset: dict) -> str:
    """Return a display name with backend hint for OpenRouter-based providers."""
    if preset.get("base_url") == _OPENROUTER_BASE:
        return f"{name} (OpenRouter)"
    return name

_VISION_PRESETS: dict = {
    "deepseek": {"base_url": "https://api.deepseek.com",                                "model": "deepseek-vl2"},
    "gemini":   {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-2.0-flash"},
    "groq":     {"base_url": "https://api.groq.com/openai/v1",                          "model": "meta-llama/llama-4-scout-17b-16e-instruct"},
    "openai":   {"base_url": "https://api.openai.com/v1",                               "model": "gpt-4o"},
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

    current_base_url = ""
    current_model = ""
    if config_exists():
        try:
            cfg = load_config()
            current_base_url = cfg.services.openai.base_url
            current_model = cfg.services.openai.model
        except Exception:
            pass

    profile_data = get_provider_data()
    all_providers = get_available_providers(
        provider_keys=profile_data.get("provider_keys"),
        custom_providers=profile_data.get("custom_providers"),
    )

    table = Table(box=box.ROUNDED, border_style="cyan", show_lines=False)
    table.add_column("Provider", style="bold")
    table.add_column("Model")
    table.add_column("Key")
    table.add_column("Type", style="dim")

    from pathlib import Path as _Path
    _has_claude_session = (_Path.home() / ".claude" / ".credentials.json").exists()

    for name, entry in all_providers.items():
        auth = entry.get("auth_type", "api_key")
        if auth == "none":
            key_status = "[green]local[/green]"
        elif auth == "bearer":
            key_status = "[green]session[/green]" if _has_claude_session else "[yellow]no session[/yellow]"
        else:
            key_status = "[green]set[/green]" if entry.get("api_key") else "[yellow]not set[/yellow]"

        is_active = (current_base_url == entry.get("base_url") and current_model == entry.get("model"))
        active_marker = " [bold cyan]*[/bold cyan]" if is_active else ""
        label = "[dim](custom)[/dim] " if not entry.get("is_builtin", True) else ""
        table.add_row(
            f"{label}{name}{active_marker}",
            entry.get("model", ""),
            key_status,
            auth,
        )

    console.print()
    console.print(table)
    console.print()
    console.print("[dim]* = currently active[/dim]")
    console.print()


@app.command("use")
def provider_use(
    provider: Optional[str] = typer.Argument(None, help="Provider name (deepseek-chat, kimi-k2, anthropic, openai, claude, kimi, gemini, groq, deepseek)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key (skips interactive prompt)"),
):
    """Switch to a provider and update the configuration."""
    from InquirerPy import inquirer as _inquirer
    from cli.config.manager import config_exists, load_config, save_config

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    if provider is None:
        from pathlib import Path as _Path
        _cfg = load_config()
        _current_base_url = _cfg.services.openai.base_url or ""
        _has_claude_session = (_Path.home() / ".claude" / ".credentials.json").exists()
        _profile_data = get_provider_data()
        _all = get_available_providers(
            provider_keys=_profile_data.get("provider_keys"),
            custom_providers=_profile_data.get("custom_providers"),
        )

        def _choice_label(name: str, entry: dict) -> str:
            is_active = (entry.get("base_url") == _current_base_url and
                         entry.get("model") == _cfg.services.openai.model)
            active = " *" if is_active else "  "
            key_ok = entry.get("api_key") or entry.get("auth_type") in ("none", "bearer")
            key_mark = "" if key_ok else " [no key]"
            custom = " (custom)" if not entry.get("is_builtin", True) else ""
            return f"{active} {name:<26}{custom} {entry.get('model','')}{key_mark}"

        choices = [
            {"name": _choice_label(n, p), "value": n}
            for n, p in _all.items()
        ]

        try:
            provider = _inquirer.select(
                message="Select provider:",
                choices=choices,
                default=next(
                    (n for n, p in _all.items() if p.get("base_url") == _current_base_url),
                    choices[0]["value"],
                ),
                pointer="❯",
                qmark="",
            ).execute()
        except KeyboardInterrupt:
            raise typer.Exit(0)

    _pd = get_provider_data()
    all_providers = get_available_providers(
        provider_keys=_pd.get("provider_keys"),
        custom_providers=_pd.get("custom_providers"),
    )
    if provider not in all_providers:
        valid = ", ".join(all_providers.keys())
        console.print(f"[red]Unknown provider:[/red] {provider}")
        console.print(f"[dim]Valid providers: {valid}[/dim]")
        raise typer.Exit(1)

    preset = all_providers[provider]

    if preset.get("auth_type") == "none":
        resolved_key = "ollama"
        console.print("[dim]No API key required for local provider.[/dim]")
    elif preset.get("auth_type") == "bearer":
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
        try:
            cfg
        except NameError:
            cfg = load_config()
        target_url = preset["base_url"]
        saved_key = cfg.services.provider_keys.get(target_url) or cfg.services.openai.api_key or ""
        active_url = cfg.services.openai.base_url or ""
        saved_key_is_for_active = saved_key and active_url == target_url

        if saved_key:
            masked = saved_key[:8] + "..." + saved_key[-4:]
            label = "API key already configured" if saved_key_is_for_active else "Saved API key found for this provider"
            try:
                action = _inquirer.select(
                    message=f"{label}: {masked}",
                    choices=[
                        {"name": "  Keep existing key", "value": "keep"},
                        {"name": "  Change to a new key", "value": "change"},
                    ],
                    pointer="❯",
                    qmark="",
                ).execute()
            except KeyboardInterrupt:
                raise typer.Exit(0)
            if action == "change":
                resolved_key = typer.prompt(f"Enter new API key for {provider}", hide_input=True)
            else:
                resolved_key = saved_key
        else:
            resolved_key = typer.prompt(f"Enter API key for {provider}", hide_input=True)

    if not resolved_key:
        console.print("[red]API key cannot be empty.[/red]")
        raise typer.Exit(1)

    try:
        cfg
    except NameError:
        cfg = load_config()
    cfg.services.openai.api_key = resolved_key
    cfg.services.openai.base_url = preset["base_url"]
    cfg.services.openai.model = preset["model"]
    cfg.services.openai.auth_type = preset["auth_type"]
    cfg.services.provider_keys[preset["base_url"]] = resolved_key
    save_config(cfg)
    update_provider(provider, resolved_key)

    console.print(f"[green]Provider switched to[/green] [bold cyan]{provider}[/bold cyan]")
    console.print(f"  Base URL : {preset['base_url']}")
    console.print(f"  Model    : {preset['model']}")
    console.print()

    _restart_service_if_running()


@app.command("add")
def provider_add(
    name: str = typer.Argument(..., help="Unique provider name (e.g. my-ollama)"),
    base_url: str = typer.Option(..., "--base-url", "-u", help="API base URL"),
    model: str = typer.Option(..., "--model", "-m", help="Model name"),
    auth_type: str = typer.Option("api_key", "--auth-type", "-a", help="none | api_key | bearer"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key (optional)"),
):
    """Register a new custom provider."""
    resolved_key = api_key or ""
    if auth_type == "api_key" and not resolved_key:
        try:
            from InquirerPy import inquirer as _inquirer
            resolved_key = _inquirer.secret(message=f"API key for {name} (leave empty to skip):").execute()
        except Exception:
            resolved_key = typer.prompt(f"API key for {name} (leave empty to skip)", default="", hide_input=True)

    save_custom_provider(name=name, base_url=base_url, model=model, auth_type=auth_type, api_key=resolved_key)
    console.print(f"[green]Provider[/green] [bold cyan]{name}[/bold cyan] [green]added[/green]")
    console.print(f"  Base URL : {base_url}")
    console.print(f"  Model    : {model}")
    console.print()
    console.print(f"[dim]Run [bold]gillie provider use {name}[/bold] to activate it.[/dim]")
    console.print()


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



@vision_app.command("set")
def vision_set(
    provider: Optional[str] = typer.Argument(None, help="Preset provider (gemini, groq, openai, openrouter)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL (overrides preset)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name (overrides preset)"),
):
    """Set the vision provider used for image description."""
    from cli.config.manager import config_exists, load_config, save_config

    from InquirerPy import inquirer as _inquirer

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    if provider is None and not base_url and not model:
        _vcfg = load_config()
        _current_vurl = _vcfg.services.vision.base_url or ""
        choices = [
            {
                "name": f"{'*' if p['base_url'] == _current_vurl else ' '}  {n:<14} {p['model']}",
                "value": n,
            }
            for n, p in _VISION_PRESETS.items()
        ] + [{"name": "    custom           (enter base-url and model manually)", "value": "__custom__"}]

        try:
            provider = _inquirer.select(
                message="Select vision provider:",
                choices=choices,
                default=next(
                    (n for n, p in _VISION_PRESETS.items() if p["base_url"] == _current_vurl),
                    choices[0]["value"],
                ),
                pointer="❯", qmark="",
            ).execute()
        except KeyboardInterrupt:
            raise typer.Exit(0)

        if provider == "__custom__":
            provider = None

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
