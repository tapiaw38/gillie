import os
import typer
from rich.console import Console
from rich.panel import Panel

from cli.config.manager import config_exists, get_config_path

console = Console()

app = typer.Typer()


@app.callback(invoke_without_command=True)
def start(
    host: str = typer.Option(None, "--host", "-h", help="Server host"),
    port: int = typer.Option(None, "--port", "-p", help="Server port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (dev mode)"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of worker processes"),
):
    """Start the Gillie API server."""
    if not config_exists():
        console.print("[red]✗[/red] No configuration found.")
        console.print("Run [bold cyan]./gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    from cli.config.manager import load_config
    config = load_config()

    actual_host = host or config.server.host
    actual_port = port or config.server.port

    os.environ["GILLIE_CONFIG"] = str(get_config_path())

    console.print()
    console.print(Panel(
        f"✨🐙 [bold cyan]Gillie[/bold cyan] — [bold]{config.profile.assistant_name}[/bold]\n"
        f"[dim]{config.profile.business_name}[/dim]",
        border_style="cyan",
    ))
    console.print(f"  Server:  [bold]http://{actual_host}:{actual_port}[/bold]")
    console.print(f"  Docs:    [bold]http://{actual_host}:{actual_port}/docs[/bold]")
    console.print(f"  Model:   [dim]{config.services.openai.model}[/dim]")
    console.print(f"  MongoDB: [dim]{config.services.mongodb.uri}[/dim]")
    if config.services.qdrant.enabled:
        console.print(f"  Qdrant:  [dim]{config.services.qdrant.host}:{config.services.qdrant.port}[/dim]")
    if config.services.brain.enabled:
        console.print(f"  Brain:   [green]✓ episodic memory active[/green]")
    console.print()

    import uvicorn
    uvicorn.run(
        "main:app",
        host=actual_host,
        port=actual_port,
        reload=reload,
        workers=workers if not reload else 1,
        log_level=config.logging.log_level.lower(),
    )
