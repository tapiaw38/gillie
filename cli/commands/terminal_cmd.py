"""
./gillie terminal — manage the Gillie Terminal (Go/Bubbletea app).

Commands:
  start    Launch the compiled terminal binary
  dev      Run from source with `go run`
  build    Compile the binary  (go build -o gillie-terminal .)
  install  Download Go dependencies (go mod tidy + go mod download)
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()
app = typer.Typer(help="Manage the Gillie Terminal (Bubbletea app).")

TERMINAL_DIR = Path(__file__).parent.parent.parent.resolve() / "terminal"
RELEASE_DIR  = Path(__file__).parent.parent.parent.resolve() / "release" / "terminal"
BINARY_NAME  = "gterm"


def _check_terminal_dir() -> None:
    if not TERMINAL_DIR.exists():
        console.print("[red]✗[/red] Terminal directory not found at [dim]./terminal[/dim]")
        raise typer.Exit(1)
    if not (TERMINAL_DIR / "go.mod").exists():
        console.print("[red]✗[/red] [dim]go.mod[/dim] not found. Is this the right directory?")
        raise typer.Exit(1)


def _check_go() -> str:
    go = shutil.which("go")
    if not go:
        console.print("[red]✗[/red] [bold]go[/bold] not found in PATH. Install Go from https://go.dev")
        raise typer.Exit(1)
    return go


def _api_flags() -> list[str]:
    """Read host/port from gillie config and return them as CLI flags."""
    try:
        from cli.config.manager import config_exists, load_config
        if config_exists():
            cfg = load_config()
            host = cfg.server.host or "127.0.0.1"
            if host == "0.0.0.0":
                host = "127.0.0.1"
            port = cfg.server.port or 8000
            return [f"--host={host}", f"--port={port}"]
    except Exception:
        pass
    return []


@app.callback(invoke_without_command=True)
def terminal(ctx: typer.Context) -> None:
    """Manage the Gillie Terminal (Bubbletea app)."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("start")
def start(
    shell: str = typer.Option("", "--shell", help="Shell to spawn (default: $SHELL)"),
    conv_id: str = typer.Option("", "--conv-id", help="Resume a specific conversation"),
) -> None:
    """Launch the compiled Gillie Terminal binary."""
    _check_terminal_dir()

    binary = RELEASE_DIR / BINARY_NAME
    if not binary.exists():
        console.print(
            "[yellow]⚠[/yellow]  Binary not found. Building first…"
        )
        console.print()
        _do_build()

    console.print()
    console.print(Panel(
        "[bold cyan]Gillie Terminal[/bold cyan]\n"
        "[dim]Ctrl+G — toggle AI panel  ·  Ctrl+Q — quit[/dim]",
        border_style="cyan",
    ))
    console.print()

    cmd = [str(binary)] + _api_flags()
    if shell:
        cmd += [f"--shell={shell}"]
    if conv_id:
        cmd += [f"--conv-id={conv_id}"]

    subprocess.run(cmd, cwd=TERMINAL_DIR)


@app.command("dev")
def dev(
    shell: str = typer.Option("", "--shell", help="Shell to spawn (default: $SHELL)"),
) -> None:
    """Run the terminal from source using `go run` (no build step)."""
    _check_terminal_dir()
    go = _check_go()

    console.print()
    console.print(Panel(
        "[bold cyan]Gillie Terminal[/bold cyan] — [bold]dev mode[/bold]\n"
        f"[dim]{TERMINAL_DIR}[/dim]",
        border_style="cyan",
    ))
    console.print()

    cmd = [go, "run", "."] + _api_flags()
    if shell:
        cmd += [f"--shell={shell}"]

    subprocess.run(cmd, cwd=TERMINAL_DIR)


@app.command("build")
def build(
    output: str = typer.Option("", "--output", "-o", help="Output binary path"),
) -> None:
    """Compile the terminal binary with `go build`."""
    _check_terminal_dir()
    _do_build(output or str(RELEASE_DIR / BINARY_NAME))


def _do_build(output: str = "") -> None:
    go = _check_go()

    if not output:
        output = str(RELEASE_DIR / BINARY_NAME)

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    console.print(f"  [cyan]▶[/cyan]  Building [bold]{BINARY_NAME}[/bold]…")
    result = subprocess.run(
        [go, "build", "-o", output, "."],
        cwd=TERMINAL_DIR,
    )
    if result.returncode != 0:
        console.print("[red]✗[/red] Build failed.")
        raise typer.Exit(result.returncode)

    console.print(f"  [green]✓[/green]  Binary at [dim]{output}[/dim]")
    console.print()


@app.command("install")
def install() -> None:
    """Download Go module dependencies (go mod tidy + go mod download)."""
    _check_terminal_dir()
    go = _check_go()

    console.print()
    console.print("[cyan]▶[/cyan]  Running [dim]go mod tidy[/dim]…")
    r = subprocess.run([go, "mod", "tidy"], cwd=TERMINAL_DIR)
    if r.returncode != 0:
        console.print("[red]✗[/red] go mod tidy failed.")
        raise typer.Exit(r.returncode)

    console.print("[cyan]▶[/cyan]  Running [dim]go mod download[/dim]…")
    r = subprocess.run([go, "mod", "download"], cwd=TERMINAL_DIR)
    if r.returncode != 0:
        console.print("[red]✗[/red] go mod download failed.")
        raise typer.Exit(r.returncode)

    console.print()
    console.print("[green]✓[/green]  Dependencies installed.")
    console.print()
    console.print("  Next:  [bold cyan]gillie terminal build[/bold cyan]")
    console.print()
