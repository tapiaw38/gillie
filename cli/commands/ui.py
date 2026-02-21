import subprocess
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

app = typer.Typer(help="Manage the Gillie UI (Vue dashboard).")

UI_DIR = Path(__file__).parent.parent.parent.resolve() / "ui"


def _check_ui_dir():
    if not UI_DIR.exists():
        console.print("[red]✗[/red] UI directory not found at [dim]./ui[/dim]")
        raise typer.Exit(1)
    if not (UI_DIR / "package.json").exists():
        console.print("[red]✗[/red] No [dim]package.json[/dim] found in UI directory.")
        raise typer.Exit(1)


def _detect_package_manager() -> str:
    if (UI_DIR / "yarn.lock").exists():
        return "yarn"
    if (UI_DIR / "pnpm-lock.yaml").exists():
        return "pnpm"
    return "npm"


def _run(args: list[str]):
    subprocess.run(args, cwd=UI_DIR, check=False)


@app.callback(invoke_without_command=True)
def ui(ctx: typer.Context):
    """Manage the Gillie UI (Vue dashboard)."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("start")
def start(
    host: str = typer.Option("localhost", "--host", "-h", help="Dev server host"),
    port: int = typer.Option(None, "--port", "-p", help="Dev server port"),
):
    """Start the UI in development mode (hot-reload)."""
    _check_ui_dir()

    pm = _detect_package_manager()

    console.print()
    console.print(Panel(
        "✨🐟 [bold cyan]Gillie UI[/bold cyan] — [bold]Development mode[/bold]\n"
        f"[dim]{UI_DIR}[/dim]",
        border_style="cyan",
    ))

    cmd = [pm, "run", "dev", "--", "--host", host]
    if port:
        cmd += ["--port", str(port)]

    console.print(f"  Package manager: [dim]{pm}[/dim]")
    console.print(f"  Command: [dim]{' '.join(cmd)}[/dim]")
    console.print()

    _run(cmd)


@app.command("build")
def build():
    """Build the UI for production."""
    _check_ui_dir()

    pm = _detect_package_manager()

    console.print()
    console.print(Panel(
        "✨🐟 [bold cyan]Gillie UI[/bold cyan] — [bold]Building for production[/bold]\n"
        f"[dim]{UI_DIR}[/dim]",
        border_style="cyan",
    ))

    _run([pm, "run", "build"])


@app.command("preview")
def preview(
    host: str = typer.Option("localhost", "--host", "-h", help="Preview server host"),
    port: int = typer.Option(None, "--port", "-p", help="Preview server port"),
):
    """Preview the production build locally."""
    _check_ui_dir()

    pm = _detect_package_manager()

    if not (UI_DIR / "dist").exists():
        console.print("[yellow]⚠[/yellow] No [dim]dist/[/dim] folder found. Run [bold cyan]gillie ui build[/bold cyan] first.")
        raise typer.Exit(1)

    console.print()
    console.print(Panel(
        "✨🐟 [bold cyan]Gillie UI[/bold cyan] — [bold]Preview mode[/bold]\n"
        f"[dim]{UI_DIR}[/dim]",
        border_style="cyan",
    ))

    cmd = [pm, "run", "preview", "--", "--host", host]
    if port:
        cmd += ["--port", str(port)]

    _run(cmd)


@app.command("install")
def install():
    """Install UI dependencies."""
    _check_ui_dir()

    pm = _detect_package_manager()

    console.print()
    console.print(f"✨🐟 Installing UI dependencies with [bold cyan]{pm}[/bold cyan]...")
    console.print()

    _run([pm, "install"])
    console.print()
    console.print("[green]✓[/green] Dependencies installed.")
