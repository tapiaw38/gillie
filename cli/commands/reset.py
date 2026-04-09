import shutil
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from InquirerPy import inquirer

from cli.config.manager import config_exists, load_config, get_config_path, get_soul_path

console = Console()

app = typer.Typer()

DEFAULT_LOCAL_STORAGE = Path.home() / ".local" / "share" / "gillie" / "storage"
CONFIG_DIR = Path.home() / ".gillie"


@app.callback(invoke_without_command=True)
def reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    keep_config: bool = typer.Option(False, "--keep-config", help="Keep ~/.gillie config files"),
    keep_storage: bool = typer.Option(False, "--keep-storage", help="Keep local storage files"),
):
    """Reset Gillie to factory state: wipe MongoDB, Qdrant and local files."""
    console.print()
    console.print(Panel(
        "[bold red]⚠  Factory Reset[/bold red]\n\n"
        "This will permanently delete:\n"
        "  • All MongoDB data (conversations, profiles, jobs, ...)\n"
        "  • All Qdrant collections (vector embeddings)\n"
        "  • Local storage files (uploaded documents, audio)\n"
        "  • CLI config files (~/.gillie/)",
        border_style="red",
    ))
    console.print()

    if not yes:
        try:
            confirm = inquirer.select(
                message="Are you sure you want to reset everything?",
                choices=[{"name": "  No, cancel", "value": False}, {"name": "  Yes, reset", "value": True}],
                pointer="❯", qmark="",
            ).execute()
        except KeyboardInterrupt:
            confirm = False
        if not confirm:
            console.print("[dim]Reset cancelled.[/dim]")
            raise typer.Exit(0)

        try:
            confirm2 = inquirer.select(
                message="This cannot be undone. Confirm again?",
                choices=[{"name": "  No, cancel", "value": False}, {"name": "  Yes, I'm sure", "value": True}],
                pointer="❯", qmark="",
            ).execute()
        except KeyboardInterrupt:
            confirm2 = False
        if not confirm2:
            console.print("[dim]Reset cancelled.[/dim]")
            raise typer.Exit(0)

    config = None
    if config_exists():
        try:
            config = load_config()
        except Exception:
            pass

    errors = []

    console.print()
    console.print("[bold]Resetting MongoDB...[/bold]")
    try:
        mongo_uri = config.services.mongodb.uri if config else "mongodb://localhost:27017"
        db_name = config.services.mongodb.database if config else "gillie-db"

        from pymongo import MongoClient
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.drop_database(db_name)
        client.close()
        console.print(f"  [green]✓[/green] Database [bold]{db_name}[/bold] dropped")
    except Exception as e:
        msg = f"MongoDB reset failed: {e}"
        console.print(f"  [yellow]⚠[/yellow]  {msg}")
        errors.append(msg)

    console.print("[bold]Resetting Qdrant...[/bold]")
    qdrant_enabled = config and config.services.qdrant.enabled if config else False
    if qdrant_enabled:
        try:
            from qdrant_client import QdrantClient

            qdrant_host = config.services.qdrant.host
            qdrant_port = config.services.qdrant.port
            qdrant_api_key = config.services.qdrant.api_key

            qclient = QdrantClient(
                host=qdrant_host,
                port=qdrant_port,
                api_key=qdrant_api_key,
                timeout=10,
            )
            collections = qclient.get_collections().collections
            if collections:
                for col in collections:
                    qclient.delete_collection(col.name)
                    console.print(f"  [green]✓[/green] Collection [bold]{col.name}[/bold] deleted")
            else:
                console.print("  [dim]No collections found[/dim]")
        except Exception as e:
            msg = f"Qdrant reset failed: {e}"
            console.print(f"  [yellow]⚠[/yellow]  {msg}")
            errors.append(msg)
    else:
        console.print("  [dim]Qdrant not enabled — skipped[/dim]")

    if not keep_storage:
        console.print("[bold]Removing local storage files...[/bold]")
        storage_path = DEFAULT_LOCAL_STORAGE
        if config and hasattr(config.services, "storage"):
            cfg_path = config.services.storage.local_path
            if cfg_path:
                storage_path = Path(cfg_path)

        if storage_path.exists():
            try:
                shutil.rmtree(storage_path)
                console.print(f"  [green]✓[/green] Removed [bold]{storage_path}[/bold]")
            except Exception as e:
                msg = f"Storage removal failed: {e}"
                console.print(f"  [yellow]⚠[/yellow]  {msg}")
                errors.append(msg)
        else:
            console.print("  [dim]No local storage directory found — skipped[/dim]")

    if not keep_config:
        console.print("[bold]Removing CLI config...[/bold]")
        for path in [get_soul_path(), get_config_path()]:
            if path.exists():
                try:
                    path.unlink()
                    console.print(f"  [green]✓[/green] Removed [bold]{path}[/bold]")
                except Exception as e:
                    msg = f"Could not remove {path}: {e}"
                    console.print(f"  [yellow]⚠[/yellow]  {msg}")
                    errors.append(msg)
        if CONFIG_DIR.exists() and not any(CONFIG_DIR.iterdir()):
            CONFIG_DIR.rmdir()

    console.print()
    if errors:
        console.print(f"[yellow]Reset completed with {len(errors)} warning(s):[/yellow]")
        for e in errors:
            console.print(f"  [yellow]•[/yellow] {e}")
    else:
        console.print("[green]✓[/green] Reset complete. Run [bold cyan]gillie init[/bold cyan] to start fresh.")
    console.print()
