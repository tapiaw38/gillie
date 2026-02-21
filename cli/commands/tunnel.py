import subprocess
import shutil
import typer
from rich.console import Console
from rich.table import Table
from rich import box

from cli.config.manager import config_exists, load_config, save_config

console = Console()

app = typer.Typer(help="Manage SSH tunnel to a remote VPS.")


def _require_config():
    if not config_exists():
        console.print("[red]✗[/red] No config found. Run [bold cyan]./gillie init[/bold cyan] first.")
        raise typer.Exit(1)


def _require_ssh():
    if not shutil.which("ssh"):
        console.print("[red]✗[/red] SSH not found. Install OpenSSH client.")
        raise typer.Exit(1)


@app.command("set")
def set_tunnel(
    host: str = typer.Option(None, "--host", "-H", help="VPS IP or hostname"),
    user: str = typer.Option(None, "--user", "-u", help="SSH user"),
    ssh_port: int = typer.Option(None, "--ssh-port", help="SSH port (default 22)"),
    api_port: int = typer.Option(None, "--api-port", help="API port on VPS (default 8000)"),
    local_port: int = typer.Option(None, "--local-port", help="Local port to expose (default 8000)"),
):
    """Configure VPS connection details for the SSH tunnel."""
    _require_config()
    config = load_config()
    t = config.tunnel

    if host is not None:
        t.host = host
    if user is not None:
        t.user = user
    if ssh_port is not None:
        t.ssh_port = ssh_port
    if api_port is not None:
        t.api_port = api_port
    if local_port is not None:
        t.local_port = local_port

    # Interactive prompts for missing required fields
    if not t.host:
        t.host = typer.prompt("VPS IP or hostname")
    if not t.user:
        t.user = typer.prompt("SSH user")

    save_config(config)

    console.print()
    console.print("[green]✓[/green] Tunnel config saved.")
    _print_tunnel_info(t)


@app.command("show")
def show():
    """Show current tunnel configuration."""
    _require_config()
    config = load_config()
    t = config.tunnel

    if not t.host or not t.user:
        console.print("[yellow]⚠[/yellow]  Tunnel not configured. Run [bold cyan]gillie tunnel set[/bold cyan] first.")
        raise typer.Exit(0)

    console.print()
    _print_tunnel_info(t)


@app.command("start")
def start(
    identity: str = typer.Option(None, "--identity", "-i", help="Path to SSH private key"),
):
    """
    Start SSH tunnel to the VPS.

    Forwards localhost:{local_port} → VPS:{api_port}.
    The frontend on your local machine can then reach the API at http://localhost:{local_port}.

    Press Ctrl+C to stop.
    """
    _require_config()
    _require_ssh()
    config = load_config()
    t = config.tunnel

    if not t.host or not t.user:
        console.print("[red]✗[/red] Tunnel not configured. Run [bold cyan]gillie tunnel set[/bold cyan] first.")
        raise typer.Exit(1)

    cmd = [
        "ssh",
        "-N",                                          # no remote command
        "-L", f"{t.local_port}:localhost:{t.api_port}",
        "-p", str(t.ssh_port),
    ]

    if identity:
        cmd += ["-i", identity]

    cmd.append(f"{t.user}@{t.host}")

    console.print()
    console.print(f"✨🐟 Starting SSH tunnel...")
    console.print(f"  [cyan]local:[/cyan]  localhost:[bold]{t.local_port}[/bold]")
    console.print(f"  [cyan]remote:[/cyan] {t.user}@{t.host}:{t.api_port}  (SSH :{t.ssh_port})")
    console.print()
    console.print(f"  Frontend can connect to [bold]http://localhost:{t.local_port}[/bold]")
    console.print()
    console.print("[dim]Press Ctrl+C to stop the tunnel.[/dim]")
    console.print()

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print()
        console.print("[green]✓[/green] Tunnel closed.")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗[/red] Failed to establish tunnel: {e}")
        raise typer.Exit(1)


def _print_tunnel_info(t):
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold dim")
    table.add_column("Value")

    table.add_row("Host", t.host or "[dim]not set[/dim]")
    table.add_row("User", t.user or "[dim]not set[/dim]")
    table.add_row("SSH port", str(t.ssh_port))
    table.add_row("API port (VPS)", str(t.api_port))
    table.add_row("Local port", str(t.local_port))
    table.add_row("Command", f"ssh -N -L {t.local_port}:localhost:{t.api_port} -p {t.ssh_port} {t.user}@{t.host}")

    console.print(table)
    console.print()
    console.print("  Start the tunnel with: [bold cyan]gillie tunnel start[/bold cyan]")
    console.print()
