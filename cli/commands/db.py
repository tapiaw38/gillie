import shutil
import subprocess
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box
from InquirerPy import inquirer

from cli.config.manager import config_exists, load_config

console = Console()

app = typer.Typer(help="Manage the local MongoDB database (Docker).")

PROJECT_DIR = Path(__file__).parent.parent.parent.resolve()
COMPOSE_FILE = PROJECT_DIR / "docker-compose.mongo.yml"
CONTAINER_NAME = "gillie-db"


def _get_compose_cmd() -> list | None:
    """Return docker compose command: v2 ['docker','compose'] or v1 ['docker-compose']."""
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
    """Return True if config says external (and warn the user)."""
    if config_exists():
        config = load_config()
        if config.services.mongodb.mode == "external":
            console.print("[yellow]⚠[/yellow]  MongoDB is configured as [bold]external[/bold].")
            console.print(f"   URI: [dim]{config.services.mongodb.uri}[/dim]")
            console.print("   No local container to manage.")
            return True
    return False


@app.command("start")
def start():
    """Start MongoDB via Docker Compose."""
    if _check_external_mode():
        raise typer.Exit(0)

    if not COMPOSE_FILE.exists():
        console.print(f"[red]✗[/red] {COMPOSE_FILE.name} not found.")
        raise typer.Exit(1)

    console.print("✨🐙 Starting MongoDB...")
    result = _compose(["up", "-d"])
    if result.returncode == 0:
        console.print("[green]✓[/green] MongoDB running at [bold]mongodb://localhost:27017[/bold]")
    else:
        console.print("[red]✗[/red] Failed to start MongoDB.")
        raise typer.Exit(result.returncode)


@app.command("stop")
def stop():
    """Stop MongoDB Docker container."""
    if _check_external_mode():
        raise typer.Exit(0)
    result = _compose(["down"])
    if result.returncode == 0:
        console.print("✨🐙 [green]✓[/green] MongoDB stopped.")


@app.command("restart")
def restart():
    """Restart MongoDB Docker container."""
    if _check_external_mode():
        raise typer.Exit(0)
    result = _compose(["restart"])
    if result.returncode == 0:
        console.print("✨🐙 [green]✓[/green] MongoDB restarted.")


@app.command("status")
def status():
    """Show MongoDB container status."""
    if config_exists():
        config = load_config()
        mode = config.services.mongodb.mode
        uri = config.services.mongodb.uri
    else:
        mode = "docker"
        uri = "mongodb://localhost:27017"

    console.print()

    if mode == "external":
        console.print(f"[cyan]MongoDB mode:[/cyan] external")
        console.print(f"[cyan]URI:[/cyan]          {uri}")
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
    table.add_row("URI", uri)

    if CONTAINER_NAME in (result.stdout or ""):
        parts = result.stdout.strip().split("\t")
        status_str = parts[1] if len(parts) > 1 else "running"
        table.add_row("Status", f"[green]● {status_str}[/green]")
    else:
        table.add_row("Status", "[dim]○ stopped[/dim]")
        console.print(table)
        console.print()
        console.print("  Start with: [bold cyan]./gillie db start[/bold cyan]")
        console.print()
        return

    console.print(table)
    console.print()


@app.command("reset")
def reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Drop all data from the MongoDB database."""
    db_name = "gillie-db"
    uri = "mongodb://localhost:27017"
    if config_exists():
        config = load_config()
        db_name = config.services.mongodb.database
        uri = config.services.mongodb.uri

    if not yes:
        console.print(f"[red]⚠[/red]  This will delete [bold]all data[/bold] in [bold]{db_name}[/bold].")
        try:
            confirm = inquirer.select(
                message="Are you sure?",
                choices=[{"name": "  No, cancel", "value": False}, {"name": "  Yes, delete all data", "value": True}],
                pointer="❯", qmark="",
            ).execute()
        except KeyboardInterrupt:
            confirm = False
        if not confirm:
            console.print("Aborted.")
            raise typer.Exit(0)

    try:
        from pymongo import MongoClient
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.drop_database(db_name)
        client.close()
        console.print(f"[green]✓[/green] Database [bold]{db_name}[/bold] dropped successfully.")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to reset database: {e}")
        raise typer.Exit(1)


@app.command("logs")
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
):
    """View MongoDB container logs."""
    if _check_external_mode():
        raise typer.Exit(0)
    args = ["logs", f"--tail={lines}"]
    if follow:
        args.append("-f")
    args.append(CONTAINER_NAME)
    _compose(args)
