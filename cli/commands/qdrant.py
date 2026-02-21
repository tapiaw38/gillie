import shutil
import subprocess
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box

from cli.config.manager import config_exists, load_config

console = Console()

app = typer.Typer(help="Manage the local Qdrant vector store (Docker).")

PROJECT_DIR = Path(__file__).parent.parent.parent.resolve()
COMPOSE_FILE = PROJECT_DIR / "docker-compose.qdrant.yml"
CONTAINER_NAME = "gillie-qdrant"


def _get_compose_cmd() -> list | None:
    if shutil.which("docker"):
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return None


def _require_docker():
    cmd = _get_compose_cmd()
    if not cmd:
        console.print("[red]✗[/red] Docker not found.")
        console.print("  Install Docker: https://docs.docker.com/engine/install/")
        raise typer.Exit(1)
    return cmd


def _compose(args: list) -> subprocess.CompletedProcess:
    cmd = _require_docker()
    full_cmd = cmd + ["-f", str(COMPOSE_FILE)] + args
    return subprocess.run(full_cmd, check=False)


def _check_external_mode() -> bool:
    """Return True if Qdrant is configured as external."""
    if config_exists():
        config = load_config()
        if not config.services.qdrant.enabled:
            console.print("[yellow]⚠[/yellow]  Qdrant is [bold]disabled[/bold] in config.")
            console.print("   Enable it with [bold cyan]gillie services edit[/bold cyan]")
            return True
        if config.services.qdrant.mode == "external":
            console.print("[yellow]⚠[/yellow]  Qdrant is configured as [bold]external[/bold].")
            console.print(f"   Host: [dim]{config.services.qdrant.host}:{config.services.qdrant.port}[/dim]")
            console.print("   No local container to manage.")
            return True
    return False


@app.command("start")
def start():
    """Start Qdrant via Docker Compose."""
    if _check_external_mode():
        raise typer.Exit(0)

    if not COMPOSE_FILE.exists():
        console.print(f"[red]✗[/red] {COMPOSE_FILE.name} not found.")
        raise typer.Exit(1)

    console.print("✨🐟 Starting Qdrant...")
    result = _compose(["up", "-d"])
    if result.returncode == 0:
        console.print("[green]✓[/green] Qdrant running at [bold]http://localhost:6333[/bold]")
    else:
        console.print("[red]✗[/red] Failed to start Qdrant.")
        raise typer.Exit(result.returncode)


@app.command("stop")
def stop():
    """Stop Qdrant Docker container."""
    if _check_external_mode():
        raise typer.Exit(0)
    result = _compose(["down"])
    if result.returncode == 0:
        console.print("✨🐟 [green]✓[/green] Qdrant stopped.")


@app.command("restart")
def restart():
    """Restart Qdrant Docker container."""
    if _check_external_mode():
        raise typer.Exit(0)
    result = _compose(["restart"])
    if result.returncode == 0:
        console.print("✨🐟 [green]✓[/green] Qdrant restarted.")


@app.command("status")
def status():
    """Show Qdrant container status."""
    if config_exists():
        config = load_config()
        qdrant_cfg = config.services.qdrant
        enabled = qdrant_cfg.enabled
        mode = qdrant_cfg.mode
        host = qdrant_cfg.host
        port = qdrant_cfg.port
    else:
        enabled = False
        mode = "docker"
        host = "localhost"
        port = 6333

    console.print()

    if not enabled:
        console.print("[dim]Qdrant is disabled. Enable it via [bold cyan]gillie services edit[/bold cyan][/dim]")
        console.print()
        return

    if mode == "external":
        console.print(f"[cyan]Qdrant mode:[/cyan] external")
        console.print(f"[cyan]Host:[/cyan]        {host}:{port}")
        console.print()
        return

    if not shutil.which("docker"):
        console.print("[yellow]⚠[/yellow] Docker not installed — cannot check container status.")
        return

    result = subprocess.run(
        [
            "docker", "ps",
            "--filter", f"name={CONTAINER_NAME}",
            "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"
        ],
        capture_output=True, text=True
    )

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold dim")
    table.add_column("Value")

    table.add_row("Mode", "docker (local)")
    table.add_row("HTTP", f"http://localhost:{port}")
    table.add_row("gRPC", f"localhost:{config.services.qdrant.grpc_port if config_exists() else 6334}")

    if CONTAINER_NAME in (result.stdout or ""):
        parts = result.stdout.strip().split("\t")
        status_str = parts[1] if len(parts) > 1 else "running"
        table.add_row("Status", f"[green]● {status_str}[/green]")
    else:
        table.add_row("Status", "[dim]○ stopped[/dim]")
        console.print(table)
        console.print()
        console.print("  Start with: [bold cyan]./gillie qdrant start[/bold cyan]")
        console.print()
        return

    console.print(table)
    console.print()


@app.command("logs")
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
):
    """View Qdrant container logs."""
    if _check_external_mode():
        raise typer.Exit(0)
    args = ["logs", f"--tail={lines}"]
    if follow:
        args.append("-f")
    args.append(CONTAINER_NAME)
    _compose(args)
