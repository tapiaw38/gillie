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
from cli.config.db import update_provider, save_custom_provider, delete_custom_provider, delete_provider, get_provider_data, get_voice_data

app = typer.Typer(help="Manage AI provider (DeepSeek, OpenRouter, Anthropic, OpenAI, etc.)")
vision_app = typer.Typer(help="Configure vision AI provider for image description")
voice_app = typer.Typer(help="Configure the OpenAI voice used for spoken replies")
image_app = typer.Typer(help="Configure image generation provider")
video_app = typer.Typer(help="Configure video generation provider")
app.add_typer(vision_app, name="vision")
app.add_typer(voice_app, name="voice")
app.add_typer(image_app, name="image")
app.add_typer(video_app, name="video")
console = Console()

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"

def _provider_display_name(name: str, preset: dict) -> str:
    """Return a display name with backend hint for OpenRouter-based providers."""
    if preset.get("base_url") == _OPENROUTER_BASE:
        return f"{name} (OpenRouter)"
    return name

_VOICE_DEFAULTS: dict = {
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o-mini-tts",
    "voice": "nova",
}

_EDGE_VOICES: dict = {
    "es-AR-ElenaNeural": "Spanish (Argentina), female",
    "es-AR-TomasNeural": "Spanish (Argentina), male",
    "es-MX-DaliaNeural": "Spanish (Mexico), female",
    "es-ES-ElviraNeural": "Spanish (Spain), female",
    "es-ES-AlvaroNeural": "Spanish (Spain), male",
    "en-US-AvaNeural": "English (US), female",
    "en-US-AndrewNeural": "English (US), male",
    "en-US-EmmaNeural": "English (US), female",
}

_VOICE_ENGINES: dict = {
    "edge": "free, no API key, neural voices",
    "openai": "paid, needs an OpenAI API key",
    "gtts": "free, robotic, offline fallback",
}

_OPENAI_VOICES: dict = {
    "alloy": "neutral, even",
    "ash": "warm, conversational",
    "ballad": "soft, expressive",
    "coral": "bright, friendly",
    "echo": "calm, low",
    "fable": "animated, storytelling",
    "nova": "clear, upbeat",
    "onyx": "deep, steady",
    "sage": "measured, gentle",
    "shimmer": "light, airy",
    "verse": "natural, versatile",
}

_VISION_PRESETS: dict = {
    "deepseek": {"base_url": "https://api.deepseek.com",                                "model": "deepseek-vl2"},
    "gemini":   {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-2.0-flash"},
    "openai":   {"base_url": "https://api.openai.com/v1",                               "model": "gpt-4o"},
}

_IMAGE_PRESETS: dict = {
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-image-1"},
    "grok": {"base_url": "https://api.x.ai/v1", "model": "grok-2-image"},
}

_VIDEO_PRESETS: dict = {
    "openai": {"base_url": "https://api.openai.com/v1", "model": "sora"},
    "grok": {"base_url": "https://api.x.ai/v1", "model": "grok-video"},
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
    profile_data = get_provider_data()
    active_provider = profile_data.get("active_provider", "")

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

    def _bearer_session_exists(entry: dict) -> bool:
        src = entry.get("token_source", "claude")
        if src == "claude":
            return (_Path.home() / ".claude" / ".credentials.json").exists()
        if src == "qwen":
            return (_Path.home() / ".qwen" / "oauth_creds.json").exists()
        if src == "codex":
            return (_Path.home() / ".codex" / "auth.json").exists()
        return False

    for name, entry in all_providers.items():
        auth = entry.get("auth_type", "api_key")
        if auth == "none":
            key_status = "[green]local[/green]"
        elif auth == "bearer":
            key_status = "[green]session[/green]" if _bearer_session_exists(entry) else "[yellow]no session[/yellow]"
        else:
            key_status = "[green]set[/green]" if entry.get("api_key") else "[yellow]not set[/yellow]"

        is_active = name == active_provider
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
    provider: Optional[str] = typer.Argument(None, help="Provider name (deepseek, kimi-k2, anthropic, openai, kimi, gemini, grok, minimax)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key (skips interactive prompt)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name (overrides preset default)"),
):
    """Switch to a provider and update the configuration."""
    from InquirerPy import inquirer as _inquirer
    from cli.config.manager import config_exists, load_config, save_config

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    if provider is None:
        _profile_data = get_provider_data()
        _active_provider = _profile_data.get("active_provider", "")
        _all = get_available_providers(
            provider_keys=_profile_data.get("provider_keys"),
            custom_providers=_profile_data.get("custom_providers"),
        )

        def _choice_label(name: str, entry: dict) -> str:
            active = " *" if name == _active_provider else "  "
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
                default=_active_provider if _active_provider in _all else choices[0]["value"],
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
        import json as _json
        from pathlib import Path as _Path

        token_source = preset.get("token_source", "claude")

        if token_source == "claude":
            default_creds_path = _Path.home() / ".claude" / ".credentials.json"
        elif token_source == "codex":
            default_creds_path = _Path.home() / ".codex" / "auth.json"
        else:
            default_creds_path = _Path.home() / ".qwen" / "oauth_creds.json"

        if api_key:
            resolved_key = api_key
        else:
            creds_path_str = str(default_creds_path)
            if not default_creds_path.exists():
                console.print(f"[yellow]Credentials file not found:[/yellow] {default_creds_path}")
                if token_source == "claude":
                    console.print("[dim]Make sure you are logged in to Claude Code (claude.ai/code)[/dim]")
                else:
                    console.print("[dim]Run [bold]qwen auth login[/bold] to authenticate.[/dim]")
                creds_path_str = typer.prompt("Path to credentials file", default=creds_path_str)
                action = "default"
            else:
                try:
                    action = _inquirer.select(
                        message=f"Credentials found at {default_creds_path}:",
                        choices=[
                            {"name": f"  Use default path ({default_creds_path})", "value": "default"},
                            {"name": "  Use a different path", "value": "custom"},
                            {"name": "  Enter token manually", "value": "manual"},
                        ],
                        pointer="❯",
                        qmark="",
                    ).execute()
                except KeyboardInterrupt:
                    raise typer.Exit(0)

            if action == "custom":
                creds_path_str = typer.prompt("Path to credentials file", default=creds_path_str)

            if action == "manual":
                resolved_key = typer.prompt("Enter bearer token", hide_input=True)
            else:
                try:
                    creds = _json.loads(_Path(creds_path_str).read_text())
                    if token_source == "claude":
                        resolved_key = creds.get("claudeAiOauth", {}).get("accessToken", "")
                    elif token_source == "codex":
                        resolved_key = creds.get("tokens", {}).get("access_token", "")
                    else:
                        resolved_key = creds.get("access_token", "")
                except Exception as e:
                    console.print(f"[red]Could not read credentials file:[/red] {e}")
                    resolved_key = ""

        if not resolved_key:
            console.print("[yellow]No token found.[/yellow]")
            raise typer.Exit(1)

        console.print(f"[dim]Using {token_source} session token.[/dim]")

        if not model:
            default_model = preset["model"]
            try:
                model_action = _inquirer.select(
                    message="Model:",
                    choices=[
                        {"name": f"  Use default ({default_model})", "value": "default"},
                        {"name": "  Enter a different model", "value": "custom"},
                    ],
                    pointer="❯",
                    qmark="",
                ).execute()
            except KeyboardInterrupt:
                raise typer.Exit(0)
            if model_action == "custom":
                model = typer.prompt("Model name", default=default_model)
            else:
                model = default_model
        preset = {**preset, "model": model}

    elif api_key:
        resolved_key = api_key
    else:
        _pd2 = get_provider_data()
        saved_key = (_pd2.get("provider_keys") or {}).get(provider, "")
        saved_key_is_for_active = saved_key and _pd2.get("active_provider") == provider

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
    console.print(f"  Model    : {cfg.services.openai.model}")
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


@app.command("edit")
def provider_edit(
    name: Optional[str] = typer.Argument(None, help="Custom provider name to edit"),
):
    """Edit a custom provider (base_url, model, auth_type, api_key)."""
    from InquirerPy import inquirer as _inquirer
    from cli.config.manager import config_exists

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    profile_data = get_provider_data()
    custom = profile_data.get("custom_providers") or {}

    if not custom:
        console.print("[yellow]No custom providers found.[/yellow] Add one with [bold cyan]gillie provider add[/bold cyan].")
        raise typer.Exit(0)

    if name is None:
        try:
            name = _inquirer.select(
                message="Select provider to edit:",
                choices=list(custom.keys()),
                pointer="❯",
                qmark="",
            ).execute()
        except KeyboardInterrupt:
            raise typer.Exit(0)

    if name not in custom:
        console.print(f"[red]Custom provider not found:[/red] {name}")
        raise typer.Exit(1)

    current = custom[name]
    console.print(f"\n[dim]Editing [bold]{name}[/bold] — press Enter to keep current value[/dim]\n")

    new_base_url = typer.prompt("Base URL", default=current.get("base_url", ""))
    new_model = typer.prompt("Model", default=current.get("model", ""))
    new_auth_type = typer.prompt("Auth type (none | api_key | bearer)", default=current.get("auth_type", "api_key"))

    provider_keys = profile_data.get("provider_keys") or {}
    current_key = provider_keys.get(name, current.get("api_key", ""))
    if new_auth_type == "api_key":
        masked = (current_key[:8] + "..." + current_key[-4:]) if len(current_key) > 12 else current_key
        hint = f" [{masked}]" if masked else ""
        new_key = typer.prompt(f"API key{hint} (Enter to keep)", default=current_key, hide_input=True)
    else:
        new_key = current_key

    save_custom_provider(
        name=name,
        base_url=new_base_url,
        model=new_model,
        auth_type=new_auth_type,
        api_key=new_key,
    )

    console.print(f"\n[green]Provider[/green] [bold cyan]{name}[/bold cyan] [green]updated.[/green]")
    console.print(f"  Base URL : {new_base_url}")
    console.print(f"  Model    : {new_model}")
    console.print()
    _restart_service_if_running()


@app.command("delete")
def provider_delete(
    name: Optional[str] = typer.Argument(None, help="Provider name to delete (built-in or custom)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a provider reference (custom entry and/or stored key)."""
    from InquirerPy import inquirer as _inquirer
    from cli.config.manager import config_exists, load_config, save_config

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    profile_data = get_provider_data()
    all_providers = get_available_providers(
        provider_keys=profile_data.get("provider_keys"),
        custom_providers=profile_data.get("custom_providers"),
    )

    if not all_providers:
        console.print("[yellow]No providers found.[/yellow]")
        raise typer.Exit(0)

    if name is None:
        try:
            name = _inquirer.select(
                message="Select provider to delete:",
                choices=[
                    {
                        "name": f"{n}{' (custom)' if not p.get('is_builtin', True) else ' (built-in)'}",
                        "value": n,
                    }
                    for n, p in all_providers.items()
                ],
                pointer="❯",
                qmark="",
            ).execute()
        except KeyboardInterrupt:
            raise typer.Exit(0)

    if name not in all_providers:
        console.print(f"[red]Provider not found:[/red] {name}")
        raise typer.Exit(1)

    if not yes:
        try:
            confirmed = _inquirer.confirm(
                message=f"Delete provider '{name}'?",
                default=False,
            ).execute()
        except KeyboardInterrupt:
            raise typer.Exit(0)
        if not confirmed:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    cfg = load_config()
    is_active = profile_data.get("active_provider", "") == name
    is_active_local = cfg.services.openai.active_provider == name

    cfg.services.provider_keys.pop(name, None)
    if is_active_local:
        cfg.services.openai.active_provider = ""
    save_config(cfg)

    if not all_providers[name].get("is_builtin", True):
        delete_custom_provider(name)
    else:
        delete_provider(name, clear_active=is_active)

    if is_active or is_active_local:
        console.print(f"[yellow]⚠[/yellow]  Deleted the active provider. Run [bold cyan]gillie provider use[/bold cyan] to switch.")

    console.print(f"[green]Provider[/green] [bold cyan]{name}[/bold cyan] [green]deleted.[/green]")
    if all_providers[name].get("is_builtin", True):
        console.print("[dim]Built-in preset remains available in code; this removed stored key/reference only.[/dim]")
    console.print()


@app.command("status")
def provider_status():
    """Show the current provider configuration."""
    profile_data = get_provider_data()
    active_provider = profile_data.get("active_provider", "")

    all_providers = get_available_providers(
        provider_keys=profile_data.get("provider_keys"),
        custom_providers=profile_data.get("custom_providers"),
    )
    entry = all_providers.get(active_provider, {})

    console.print()
    console.print(f"[bold]Provider :[/bold] [cyan]{active_provider or '(none)'}[/cyan]")
    console.print(f"[bold]Base URL :[/bold] {entry.get('base_url', '')}")
    console.print(f"[bold]Model    :[/bold] {entry.get('model', '')}")
    key_status = "[green]present[/green]" if entry.get("api_key") else "[red]missing[/red]"
    console.print(f"[bold]API key  :[/bold] {key_status}")
    console.print()



@vision_app.command("set")
def vision_set(
    provider: Optional[str] = typer.Argument(None, help="Preset provider (deepseek, gemini, openai)"),
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


def _resolve_openai_key(api_key: Optional[str], current_key: str) -> tuple[str, str]:
    if api_key:
        return api_key, "flag"
    if current_key:
        return current_key, "voice config"

    profile_data = get_provider_data()
    providers = get_available_providers(
        provider_keys=profile_data.get("provider_keys"),
        custom_providers=profile_data.get("custom_providers"),
    )
    stored = (providers.get("openai") or {}).get("api_key", "")
    if stored:
        return stored, "openai provider"

    return typer.prompt("Enter OpenAI API key", hide_input=True), "prompt"


@voice_app.command("set")
def voice_set(
    engine: Optional[str] = typer.Option(None, "--engine", "-e", help=f"Engine ({', '.join(_VOICE_ENGINES)})"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="OpenAI API key (openai engine only)"),
    voice: Optional[str] = typer.Option(None, "--voice", "-v", help="Voice name for the chosen engine"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="TTS model (openai engine only)"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL override (openai engine only)"),
):
    """Set the engine and voice used for spoken replies."""
    from cli.config.manager import config_exists, load_config, save_config
    from InquirerPy import inquirer as _inquirer

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    cfg = load_config()
    current = cfg.services.tts

    if engine is None:
        try:
            engine = _inquirer.select(
                message="Select speech engine:",
                choices=[
                    {"name": f"{'*' if name == (current.engine or 'edge') else ' '}  {name:<8} {desc}", "value": name}
                    for name, desc in _VOICE_ENGINES.items()
                ],
                default=current.engine or "edge",
                pointer="❯", qmark="",
            ).execute()
        except KeyboardInterrupt:
            raise typer.Exit(0)

    if engine not in _VOICE_ENGINES:
        console.print(f"[red]Unknown engine:[/red] {engine}")
        console.print(f"[dim]Known engines: {', '.join(_VOICE_ENGINES)}[/dim]")
        raise typer.Exit(1)

    if engine == "gtts":
        cfg.services.tts.engine = "gtts"
        cfg.services.tts.voice = ""
        cfg.services.tts.enabled = True
        save_config(cfg)
        console.print("\n[green]Engine set:[/green] [bold cyan]gtts[/bold cyan] — free, robotic, offline fallback\n")
        _restart_service_if_running()
        return

    catalog = _EDGE_VOICES if engine == "edge" else _OPENAI_VOICES
    width = 20 if engine == "edge" else 10

    if voice is None:
        try:
            voice = _inquirer.select(
                message="Select voice:",
                choices=[
                    {"name": f"{'*' if name == current.voice else ' '}  {name:<{width}} {desc}", "value": name}
                    for name, desc in catalog.items()
                ],
                default=current.voice if current.voice in catalog else next(iter(catalog)),
                pointer="❯", qmark="",
            ).execute()
        except KeyboardInterrupt:
            raise typer.Exit(0)

    if voice not in catalog:
        console.print(f"[red]Unknown voice for the {engine} engine:[/red] {voice}")
        console.print(f"[dim]Known voices: {', '.join(catalog)}[/dim]")
        raise typer.Exit(1)

    key_source = ""
    if engine == "openai":
        resolved_key, key_source = _resolve_openai_key(api_key, current.api_key)
        if not resolved_key:
            console.print("[red]API key cannot be empty.[/red]")
            raise typer.Exit(1)
        cfg.services.tts.api_key = resolved_key
        cfg.services.tts.model = model or current.model or _VOICE_DEFAULTS["model"]
        cfg.services.tts.base_url = base_url or current.base_url or _VOICE_DEFAULTS["base_url"]

    cfg.services.tts.engine = engine
    cfg.services.tts.voice = voice
    cfg.services.tts.enabled = True
    save_config(cfg)

    console.print(f"\n[green]Voice set:[/green] [bold cyan]{voice}[/bold cyan] — {catalog[voice]}")
    console.print(f"  Engine   : {engine}")
    if engine == "openai":
        console.print(f"  Model    : {cfg.services.tts.model}")
        console.print(f"  Base URL : {cfg.services.tts.base_url}")
        if key_source == "openai provider":
            console.print("  API key  : [dim]reused from the openai provider[/dim]")
    else:
        console.print("  API key  : [dim]not required[/dim]")
    console.print()
    _restart_service_if_running()


@voice_app.command("status")
def voice_status():
    """Show the current voice configuration."""
    from cli.config.manager import config_exists, load_config

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    t = load_config().services.tts
    profile = get_voice_data()
    profile_engine = (profile.get("tts_engine") or "").lower()
    profile_voice = profile.get("tts_voice") or ""

    config_engine = (t.engine or ("openai" if t.api_key else "gtts")).lower()
    engine = profile_engine or config_engine
    voice = profile_voice or t.voice

    if engine == "openai" and not t.api_key:
        console.print(
            f"\n[yellow]![/yellow] The [bold]openai[/bold] engine is selected but no API key is configured, "
            "so replies fall back to gTTS."
        )
        console.print("[dim]Run [bold]gillie provider voice set --engine openai[/bold] to add one.[/dim]")

    console.print()
    console.print(f"[bold]Spoken replies :[/bold] {'[green]on[/green]' if t.enabled else '[dim]off[/dim]'}")
    console.print(f"[bold]Engine         :[/bold] [cyan]{engine}[/cyan] [dim]— {_VOICE_ENGINES.get(engine, '')}[/dim]")

    if engine == "openai":
        console.print(f"[bold]Voice          :[/bold] {voice or _VOICE_DEFAULTS['voice']}")
        console.print(f"[bold]Model          :[/bold] {t.model or _VOICE_DEFAULTS['model']}")
        console.print(f"[bold]Base URL       :[/bold] {t.base_url or _VOICE_DEFAULTS['base_url']}")
        key_status = "[green]present[/green]" if t.api_key else "[red]missing[/red]"
        console.print(f"[bold]API key        :[/bold] {key_status}")
    elif engine == "edge":
        console.print(f"[bold]Voice          :[/bold] {voice or '[dim]auto by language[/dim]'}")
        console.print("[bold]API key        :[/bold] [dim]not required[/dim]")
    else:
        console.print("[dim]Run [bold]gillie provider voice set[/bold] for neural voices.[/dim]")

    if profile_engine and profile_engine != config_engine:
        console.print(
            f"[bold]Source         :[/bold] assistant profile "
            f"[dim](overrides the CLI setting: {config_engine})[/dim]"
        )
    elif profile_engine:
        console.print("[bold]Source         :[/bold] assistant profile [dim](matches the CLI setting)[/dim]")
    else:
        console.print("[bold]Source         :[/bold] CLI config [dim](no profile override)[/dim]")
    console.print()


@voice_app.command("clear")
def voice_clear():
    """Reset the engine, voice, and key so spoken replies fall back to gTTS."""
    from cli.config.manager import config_exists, load_config, save_config

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    cfg = load_config()
    cfg.services.tts.engine = ""
    cfg.services.tts.api_key = ""
    cfg.services.tts.voice = ""
    cfg.services.tts.model = ""
    cfg.services.tts.base_url = ""
    save_config(cfg)

    console.print("\n[green]Voice configuration cleared.[/green] Spoken replies now use gTTS.\n")
    _restart_service_if_running()


@vision_app.command("use")
def vision_use(
    provider: Optional[str] = typer.Argument(None, help="Provider name (preset or custom from `provider add`)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key override"),
):
    """Use an existing provider (preset/custom) for describe_image tool."""
    _use_media_provider("vision", provider, api_key)


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


def _set_media_provider(target: str, presets: dict, provider: Optional[str], api_key: Optional[str], base_url: Optional[str], model: Optional[str]) -> None:
    from cli.config.manager import config_exists, load_config, save_config
    from InquirerPy import inquirer as _inquirer

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    cfg = load_config()

    profile_data = get_provider_data()
    all_providers = get_available_providers(
        provider_keys=profile_data.get("provider_keys"),
        custom_providers=profile_data.get("custom_providers"),
    )

    if provider is None and not base_url and not model:
        current = getattr(cfg.services, target)
        current_url = current.base_url or ""
        current_model = current.model or ""
        choices = [
            {
                "name": f"{'*' if p['base_url'] == current_url else ' '}  {n:<10} {p['model']}",
                "value": n,
            }
            for n, p in presets.items()
        ]

        custom_choices = [
            {
                "name": f"{'*' if (entry.get('base_url') == current_url and entry.get('model') == current_model) else ' '}  {name:<10} {entry.get('model', '')} (custom)",
                "value": name,
            }
            for name, entry in all_providers.items()
            if not entry.get("is_builtin", True)
        ]
        choices.extend(custom_choices)
        choices.append({"name": "    custom     (enter base-url and model manually)", "value": "__custom__"})

        default_provider = next(
            (
                name for name, entry in all_providers.items()
                if entry.get("base_url") == current_url and entry.get("model") == current_model
            ),
            choices[0]["value"],
        )

        try:
            provider = _inquirer.select(
                message=f"Select {target.replace('_', ' ')} provider:",
                choices=choices,
                default=default_provider,
                pointer="❯",
                qmark="",
            ).execute()
        except KeyboardInterrupt:
            raise typer.Exit(0)

        if provider == "__custom__":
            provider = None

    preset = presets.get(provider, {}) if provider else {}
    if not preset and provider:
        candidate = all_providers.get(provider)
        if candidate:
            preset = {
                "base_url": candidate.get("base_url", ""),
                "model": candidate.get("model", ""),
                "auth_type": candidate.get("auth_type", "api_key"),
                "api_key": candidate.get("api_key", ""),
            }
        else:
            valid = ", ".join(sorted(set(list(presets.keys()) + list(all_providers.keys()))))
            console.print(f"[red]Unknown provider:[/red] {provider}")
            console.print(f"[dim]Known providers: {valid}[/dim]")
            raise typer.Exit(1)

    resolved_key = api_key or preset.get("api_key") or typer.prompt(f"Enter {target.replace('_', ' ')} API key", hide_input=True)
    if not resolved_key:
        console.print("[red]API key cannot be empty.[/red]")
        raise typer.Exit(1)

    resolved_base_url = base_url or preset.get("base_url", "")
    resolved_model = model or preset.get("model", "")
    if not resolved_base_url:
        resolved_base_url = typer.prompt("Base URL")
    if not resolved_model:
        resolved_model = typer.prompt("Model name")

    service_cfg = getattr(cfg.services, target)
    service_cfg.api_key = resolved_key
    service_cfg.base_url = resolved_base_url
    service_cfg.model = resolved_model
    save_config(cfg)

    label = provider or "custom"
    console.print(f"\n[green]{target.replace('_', ' ').title()} provider set:[/green] [bold cyan]{label}[/bold cyan]")
    console.print(f"  Base URL : {resolved_base_url}")
    console.print(f"  Model    : {resolved_model}")
    console.print()
    _restart_service_if_running()


def _use_media_provider(target: str, provider: Optional[str], api_key: Optional[str] = None) -> None:
    from cli.config.manager import config_exists, load_config, save_config
    from InquirerPy import inquirer as _inquirer

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    profile_data = get_provider_data()
    all_providers = get_available_providers(
        provider_keys=profile_data.get("provider_keys"),
        custom_providers=profile_data.get("custom_providers"),
    )

    if not all_providers:
        console.print("[red]No providers available.[/red]")
        raise typer.Exit(1)

    if provider is None:
        choices = [
            {
                "name": f"{name:<16} {entry.get('model', '')}{' (custom)' if not entry.get('is_builtin', True) else ''}",
                "value": name,
            }
            for name, entry in all_providers.items()
        ]
        try:
            provider = _inquirer.select(
                message=f"Select provider for {target.replace('_', ' ')}:",
                choices=choices,
                pointer="❯",
                qmark="",
            ).execute()
        except KeyboardInterrupt:
            raise typer.Exit(0)

    selected = all_providers.get(provider)
    if not selected:
        valid = ", ".join(all_providers.keys())
        console.print(f"[red]Unknown provider:[/red] {provider}")
        console.print(f"[dim]Valid providers: {valid}[/dim]")
        raise typer.Exit(1)

    resolved_key = api_key or selected.get("api_key", "")
    auth_type = selected.get("auth_type", "api_key")
    if auth_type == "none":
        resolved_key = "ollama"
    elif auth_type == "api_key" and not resolved_key:
        resolved_key = typer.prompt(f"Enter API key for {provider}", hide_input=True)

    if auth_type != "none" and not resolved_key:
        console.print("[red]API key cannot be empty.[/red]")
        raise typer.Exit(1)

    cfg = load_config()
    service_cfg = getattr(cfg.services, target)
    service_cfg.api_key = resolved_key
    service_cfg.base_url = selected.get("base_url", "")
    service_cfg.model = selected.get("model", "")
    save_config(cfg)

    console.print(f"[green]{target.replace('_', ' ').title()} provider switched to[/green] [bold cyan]{provider}[/bold cyan]")
    console.print(f"  Base URL : {service_cfg.base_url}")
    console.print(f"  Model    : {service_cfg.model}")
    console.print()
    _restart_service_if_running()


def _media_provider_status(target: str, presets: dict) -> None:
    from cli.config.manager import config_exists, load_config

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    cfg = load_config()
    p = getattr(cfg.services, target)
    profile_data = get_provider_data()
    all_providers = get_available_providers(
        provider_keys=profile_data.get("provider_keys"),
        custom_providers=profile_data.get("custom_providers"),
    )
    active = next(
        (
            name for name, entry in all_providers.items()
            if entry.get("base_url") == p.base_url and entry.get("model") == p.model
        ),
        "custom" if p.base_url else "not configured",
    )
    console.print()
    console.print(f"[bold]Provider :[/bold] [cyan]{active}[/cyan]")
    console.print(f"[bold]Base URL :[/bold] {p.base_url or '[dim]-[/dim]'}")
    console.print(f"[bold]Model    :[/bold] {p.model or '[dim]-[/dim]'}")
    key_status = "[green]present[/green]" if p.api_key else "[red]missing[/red]"
    console.print(f"[bold]API key  :[/bold] {key_status}")
    console.print()


def _media_provider_clear(target: str) -> None:
    from cli.config.manager import config_exists, load_config, save_config

    if not config_exists():
        console.print("[red]Not initialized.[/red] Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    cfg = load_config()
    p = getattr(cfg.services, target)
    p.api_key = ""
    p.base_url = ""
    p.model = ""
    save_config(cfg)
    console.print(f"[yellow]{target.replace('_', ' ').title()} provider cleared.[/yellow]")
    _restart_service_if_running()


@image_app.command("set")
def image_set(
    provider: Optional[str] = typer.Argument(None, help="Preset provider (openai, grok)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL (overrides preset)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name (overrides preset)"),
):
    """Set provider used by generate_image tool."""
    _set_media_provider("image_generation", _IMAGE_PRESETS, provider, api_key, base_url, model)


@image_app.command("status")
def image_status():
    """Show image generation provider configuration."""
    _media_provider_status("image_generation", _IMAGE_PRESETS)


@image_app.command("use")
def image_use(
    provider: Optional[str] = typer.Argument(None, help="Provider name (preset or custom from `provider add`)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key override"),
):
    """Use an existing provider (preset/custom) for generate_image tool."""
    _use_media_provider("image_generation", provider, api_key)


@image_app.command("clear")
def image_clear():
    """Clear image generation provider configuration."""
    _media_provider_clear("image_generation")


@video_app.command("set")
def video_set(
    provider: Optional[str] = typer.Argument(None, help="Preset provider (openai, grok)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL (overrides preset)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name (overrides preset)"),
):
    """Set provider used by generate_video tool."""
    _set_media_provider("video_generation", _VIDEO_PRESETS, provider, api_key, base_url, model)


@video_app.command("status")
def video_status():
    """Show video generation provider configuration."""
    _media_provider_status("video_generation", _VIDEO_PRESETS)


@video_app.command("use")
def video_use(
    provider: Optional[str] = typer.Argument(None, help="Provider name (preset or custom from `provider add`)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key override"),
):
    """Use an existing provider (preset/custom) for generate_video tool."""
    _use_media_provider("video_generation", provider, api_key)


@video_app.command("clear")
def video_clear():
    """Clear video generation provider configuration."""
    _media_provider_clear("video_generation")
