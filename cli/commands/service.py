import subprocess
import typer
from pathlib import Path
from rich.console import Console

from cli.config.manager import config_exists, load_config

console = Console()

app = typer.Typer(help="Manage the Gillie systemd service.")

PROJECT_DIR = Path(__file__).parent.parent.parent.resolve()
SERVICE_NAME = "gillie"
USER_UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
SYSTEM_UNIT_DIR = Path("/etc/systemd/system")


def _unit_path(system: bool) -> Path:
    base = SYSTEM_UNIT_DIR if system else USER_UNIT_DIR
    return base / f"{SERVICE_NAME}.service"


def _systemctl(args: list, system: bool) -> subprocess.CompletedProcess:
    cmd = ["systemctl"]
    if not system:
        cmd.append("--user")
    return subprocess.run(cmd + args, check=False)


def _generate_unit(system: bool) -> str:
    config = load_config()
    venv_python = PROJECT_DIR / ".venv" / "bin" / "python"
    python_bin = str(venv_python) if venv_python.exists() else "python3"

    host = config.server.host
    port = config.server.port
    config_path = Path.home() / ".gillie" / "config.json"

    exec_start = (
        f"{python_bin} -m uvicorn main:app "
        f"--host {host} --port {port}"
    )

    if system:
        user_section = f"User={_get_current_user()}\n"
    else:
        user_section = ""

    return f"""[Unit]
Description=Gillie API Server
After=network.target

[Service]
Type=simple
WorkingDirectory={PROJECT_DIR}
{user_section}ExecStart={exec_start}
Environment=GILLIE_CONFIG={config_path}
Restart=on-failure
RestartSec=5

[Install]
WantedBy={'multi-user.target' if system else 'default.target'}
"""


def _get_current_user() -> str:
    import os
    return os.environ.get("SUDO_USER") or os.environ.get("USER") or "nobody"


def _check_config():
    if not config_exists():
        console.print("[red]✗[/red] No configuration found. Run [bold cyan]./gillie init[/bold cyan] first.")
        raise typer.Exit(1)


def _check_linger_status() -> bool:
    """Check if loginctl linger is enabled for current user."""
    try:
        result = subprocess.run(
            ["loginctl", "show-user", _get_current_user()],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("Linger="):
                    return line.split("=")[1].strip().lower() == "yes"
        return False
    except Exception:
        return False


def _enable_linger() -> bool:
    """Enable loginctl linger for user services to persist without SSH."""
    user = _get_current_user()
    try:
        result = subprocess.run(
            ["sudo", "loginctl", "enable-linger", user],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            console.print(f"[green]✓[/green] User linger enabled for {user}")
            return True
        else:
            console.print(
                f"[yellow]⚠[/yellow]  Could not enable linger (requires sudo). "
                f"Run: [bold]sudo loginctl enable-linger {user}[/bold]"
            )
            console.print(
                "[dim]Without linger, user services stop when SSH session ends.[/dim]"
            )
            return False
    except Exception:
        console.print(
            f"[yellow]⚠[/yellow]  Linger setup failed. "
            f"Manually run: [bold]sudo loginctl enable-linger {user}[/bold]"
        )
        return False


@app.command("install")
def install(
    system: bool = typer.Option(False, "--system", help="Install as system service (requires sudo)"),
):
    """Install the systemd service unit file."""
    _check_config()

    unit_path = _unit_path(system)

    if not system:
        USER_UNIT_DIR.mkdir(parents=True, exist_ok=True)

    unit_content = _generate_unit(system)
    unit_path.write_text(unit_content)
    console.print(f"✨🐙 [green]✓[/green] Unit file written: [dim]{unit_path}[/dim]")

    _systemctl(["daemon-reload"], system)

    result = _systemctl(["enable", SERVICE_NAME], system)
    if result.returncode == 0:
        console.print(f"[green]✓[/green] Service enabled.")

        if not system:
            if not _check_linger_status():
                console.print()
                console.print("[cyan]ℹ[/cyan]  Configuring user service persistence...")
                _enable_linger()

        console.print()
        console.print(f"Start with: [bold cyan]./gillie service start[/bold cyan]")
    else:
        console.print("[red]✗[/red] Failed to enable service.")
        raise typer.Exit(result.returncode)


@app.command("uninstall")
def uninstall(
    system: bool = typer.Option(False, "--system", help="Uninstall system service"),
):
    """Disable and remove the systemd service unit file."""
    _systemctl(["disable", "--now", SERVICE_NAME], system)

    unit_path = _unit_path(system)
    if unit_path.exists():
        unit_path.unlink()
        console.print(f"[green]✓[/green] Unit file removed: [dim]{unit_path}[/dim]")

    _systemctl(["daemon-reload"], system)
    console.print("✨🐙 [green]✓[/green] Service uninstalled.")


@app.command("start")
def start(
    system: bool = typer.Option(False, "--system", help="Manage system service"),
):
    """Start the Gillie service."""
    result = _systemctl(["start", SERVICE_NAME], system)
    if result.returncode == 0:
        console.print("✨🐙 [green]✓[/green] Service started.")

        if not system and not _check_linger_status():
            console.print()
            console.print(
                "[yellow]⚠[/yellow]  User linger not enabled. "
                f"Service will stop when SSH session ends."
            )
            console.print(
                f"   Fix: [bold]sudo loginctl enable-linger {_get_current_user()}[/bold]"
            )
    else:
        console.print("[red]✗[/red] Failed to start service.")
        raise typer.Exit(result.returncode)


@app.command("stop")
def stop(
    system: bool = typer.Option(False, "--system", help="Manage system service"),
):
    """Stop the Gillie service."""
    result = _systemctl(["stop", SERVICE_NAME], system)
    if result.returncode == 0:
        console.print("✨🐙 [green]✓[/green] Service stopped.")
    else:
        console.print("[red]✗[/red] Failed to stop service.")
        raise typer.Exit(result.returncode)


@app.command("restart")
def restart(
    system: bool = typer.Option(False, "--system", help="Manage system service"),
):
    """Restart the Gillie service."""
    result = _systemctl(["restart", SERVICE_NAME], system)
    if result.returncode == 0:
        console.print("✨🐙 [green]✓[/green] Service restarted.")
    else:
        console.print("[red]✗[/red] Failed to restart service.")
        raise typer.Exit(result.returncode)


@app.command("status")
def status(
    system: bool = typer.Option(False, "--system", help="Manage system service"),
):
    """Show the service status."""
    _systemctl(["status", SERVICE_NAME], system)

    if not system:
        linger_enabled = _check_linger_status()
        console.print()
        if linger_enabled:
            console.print("[green]✓[/green] User linger: enabled (service persists without SSH)")
        else:
            console.print(
                "[yellow]⚠[/yellow]  User linger: disabled (service stops when SSH ends)"
            )
            console.print(
                f"   Fix: [bold]sudo loginctl enable-linger {_get_current_user()}[/bold]"
            )


@app.command("logs")
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
    system: bool = typer.Option(False, "--system", help="Manage system service"),
):
    """View service logs via journalctl."""
    cmd = ["journalctl", f"-n{lines}", "-u", SERVICE_NAME]
    if not system:
        cmd.append("--user")
    if follow:
        cmd.append("-f")
    subprocess.run(cmd, check=False)
