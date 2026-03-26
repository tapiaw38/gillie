import os
import subprocess
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

app = typer.Typer(help="Manage the Gillie UI (Electron app).")

UI_DIR = Path(__file__).parent.parent.parent.resolve() / "ui"


def _check_ui_dir():
    if not UI_DIR.exists():
        console.print("[red]✗[/red] UI directory not found at [dim]./ui[/dim]")
        raise typer.Exit(1)
    if not (UI_DIR / "package.json").exists():
        console.print("[red]✗[/red] [dim]package.json[/dim] not found in the UI directory.")
        raise typer.Exit(1)


def _detect_package_manager() -> str:
    if (UI_DIR / "yarn.lock").exists():
        return "yarn"
    if (UI_DIR / "pnpm-lock.yaml").exists():
        return "pnpm"
    return "npm"


def _run(args: list[str], check: bool = True) -> int:
    result = subprocess.run(args, cwd=UI_DIR)
    if check and result.returncode != 0:
        console.print(f"[red]✗[/red] Command failed: [dim]{' '.join(args)}[/dim]")
        raise typer.Exit(result.returncode)
    return result.returncode


def _ensure_dependencies(pm: str):
    node_modules = UI_DIR / "node_modules"
    if not node_modules.exists():
        console.print("  [yellow]⚠[/yellow]  [dim]node_modules[/dim] not found. Installing dependencies...")
        console.print()
        _run([pm, "install"])
        console.print()
        console.print("  [green]✓[/green] Dependencies installed.")
        console.print()


def _ensure_build(pm: str, force: bool = False):
    renderer_index = UI_DIR / "out" / "renderer" / "index.html"
    if force or not renderer_index.exists():
        if force:
            console.print("  [yellow]⚠[/yellow]  Forced rebuild...")
        else:
            console.print("  [yellow]⚠[/yellow]  Build not found. Compiling...")
        console.print()
        _run([pm, "run", "build"])
        console.print()
        console.print("  [green]✓[/green] Build completed.")
        console.print()


@app.callback(invoke_without_command=True)
def ui(ctx: typer.Context):
    """Manage the Gillie UI (Electron app)."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("start")
def start(
    rebuild: bool = typer.Option(False, "--rebuild", "-r", help="Force rebuild before starting"),
):
    """Install dependencies, build if needed, and launch the Electron app."""
    _check_ui_dir()

    pm = _detect_package_manager()

    console.print()
    console.print(Panel(
        "🐟 [bold cyan]Gillie UI[/bold cyan] — [bold]Starting app[/bold]\n"
        f"[dim]{UI_DIR}[/dim]",
        border_style="cyan",
    ))
    console.print()

    _ensure_dependencies(pm)
    _ensure_build(pm, force=rebuild)

    console.print("  [cyan]▶[/cyan]  Opening Gillie UI...")
    console.print()

    electron_bin = UI_DIR / "node_modules" / ".bin" / "electron"
    if not electron_bin.exists():
        console.print("[red]✗[/red] Electron binary not found. Run [bold cyan]gillie ui install[/bold cyan].")
        raise typer.Exit(1)

    cmd = [str(electron_bin), "."]

    env = os.environ.copy()

    if os.environ.get("WAYLAND_DISPLAY"):
        cmd += [
            "--ozone-platform=wayland",
            "--enable-features=WaylandWindowDecorations",
            "--use-angle=swiftshader",
        ]
        env["ELECTRON_OZONE_PLATFORM_HINT"] = "wayland"
    elif not os.environ.get("DISPLAY"):
        cmd += ["--ozone-platform-hint=auto", "--use-angle=swiftshader"]
        env.setdefault("ELECTRON_OZONE_PLATFORM_HINT", "auto")

    subprocess.run(cmd, cwd=UI_DIR, env=env)


@app.command("dev")
def dev(
    host: str = typer.Option("localhost", "--host", "-h", help="Dev server host"),
    port: int = typer.Option(None, "--port", "-p", help="Dev server port"),
):
    """Start the UI in development mode with hot-reload."""
    _check_ui_dir()

    pm = _detect_package_manager()

    console.print()
    console.print(Panel(
        "🐟 [bold cyan]Gillie UI[/bold cyan] — [bold]Development mode[/bold]\n"
        f"[dim]{UI_DIR}[/dim]",
        border_style="cyan",
    ))
    console.print()

    _ensure_dependencies(pm)

    cmd = [pm, "run", "dev"]
    if host != "localhost":
        cmd += ["--", "--host", host]
    if port:
        cmd += ["--port", str(port)]

    console.print(f"  Command: [dim]{' '.join(cmd)}[/dim]")
    console.print()

    _run(cmd, check=False)


@app.command("build")
def build(
    package: bool = typer.Option(False, "--package", "-p", help="Generate installer (.AppImage, .deb, .dmg, .exe)"),
):
    """Compile the UI for production."""
    _check_ui_dir()

    pm = _detect_package_manager()

    console.print()
    console.print(Panel(
        "🐟 [bold cyan]Gillie UI[/bold cyan] — [bold]Production build[/bold]\n"
        f"[dim]{UI_DIR}[/dim]",
        border_style="cyan",
    ))
    console.print()

    _ensure_dependencies(pm)

    if package:
        console.print("  Packaging as installer...")
        console.print()
        _run([pm, "run", "electron:build"])
        console.print()
        console.print("  [green]✓[/green] Installer generated in [dim]./ui/dist/[/dim]")
    else:
        _run([pm, "run", "build"])
        console.print()
        console.print("  [green]✓[/green] Build completed in [dim]./ui/out/[/dim]")


@app.command("install")
def install():
    """Install UI dependencies (node_modules)."""
    _check_ui_dir()

    pm = _detect_package_manager()

    console.print()
    console.print(f"🐟 Installing dependencies with [bold cyan]{pm}[/bold cyan]...")
    console.print()

    _run([pm, "install"])
    console.print()
    console.print("[green]✓[/green] Dependencies installed.")
