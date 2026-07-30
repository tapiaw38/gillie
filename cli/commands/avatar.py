import atexit
import contextlib
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()
app = typer.Typer(help="Manage the Persona avatar companion app.")

AVATAR_DIR = Path(__file__).parent.parent.parent.resolve() / "avatar"
DEFAULT_BRIDGE_PORT = 47831


def _check_avatar_dir() -> None:
    if not AVATAR_DIR.exists():
        console.print("[red]✗[/red] Avatar directory not found at [dim]./avatar[/dim]")
        raise typer.Exit(1)
    if not (AVATAR_DIR / "package.json").exists():
        console.print("[red]✗[/red] [dim]package.json[/dim] not found in the avatar directory.")
        raise typer.Exit(1)


def _run(args: list[str]) -> None:
    result = subprocess.run(args, cwd=AVATAR_DIR)
    if result.returncode != 0:
        console.print(f"[red]✗[/red] Command failed: [dim]{' '.join(args)}[/dim]")
        raise typer.Exit(result.returncode)


def _ensure_dependencies() -> None:
    if (AVATAR_DIR / "node_modules").exists():
        return
    console.print("  [yellow]⚠[/yellow] Installing avatar dependencies...")
    _run(["npm", "install"])


def _ensure_build(rebuild: bool) -> None:
    if not rebuild and (AVATAR_DIR / "dist" / "index.html").exists():
        return
    console.print("  [cyan]▶[/cyan] Building avatar...")
    _run(["npm", "run", "build"])


@app.command("start")
def start(
    rebuild: bool = typer.Option(False, "--rebuild", "-r", help="Force renderer rebuild"),
    background: bool = typer.Option(False, "--background", "-b", help="Start hidden in background"),
    port: int | None = typer.Option(None, "--port", help="Persona bridge port"),
):
    """Install, build, and launch Persona avatar."""
    _check_avatar_dir()

    console.print()
    console.print(Panel(
        "🐙 [bold cyan]Gillie Avatar[/bold cyan] — [bold]Starting Persona[/bold]\n"
        f"[dim]{AVATAR_DIR}[/dim]",
        border_style="cyan",
    ))
    console.print()

    _ensure_dependencies()
    _ensure_build(rebuild)

    cmd, env = _build_launch(background=background, port=port)
    console.print("  [cyan]▶[/cyan] Opening avatar...")
    subprocess.run(cmd, cwd=AVATAR_DIR, env=env)


def _build_launch(background: bool = False, port: int | None = None) -> tuple[list[str], dict]:
    electron_bin = AVATAR_DIR / "node_modules" / ".bin" / "electron"
    if not electron_bin.exists():
        console.print("[red]✗[/red] Electron binary not found after npm install.")
        raise typer.Exit(1)

    # Arch + Wayland can initialize Electron without rendering a visible window
    # when VA-API fails. Persona only needs software compositing here.
    cmd = [
        str(electron_bin),
        "--disable-gpu",
        "--disable-gpu-compositing",
        ".",
    ]
    if background:
        cmd.append("--background")

    env = os.environ.copy()
    if port is not None:
        env["PERSONA_BRIDGE_PORT"] = str(port)

    if os.environ.get("WAYLAND_DISPLAY"):
        cmd += ["--ozone-platform=wayland", "--enable-features=WaylandWindowDecorations"]
        env["ELECTRON_OZONE_PLATFORM_HINT"] = "wayland"
    elif not os.environ.get("DISPLAY"):
        cmd += ["--ozone-platform-hint=auto", "--disable-gpu"]
        env.setdefault("ELECTRON_OZONE_PLATFORM_HINT", "auto")

    return cmd, env


def spawn(port: int | None = None) -> subprocess.Popen:
    """Launch the avatar without blocking the caller."""
    _check_avatar_dir()
    _ensure_dependencies()
    _ensure_build(rebuild=False)
    cmd, env = _build_launch(port=port)
    return subprocess.Popen(cmd, cwd=AVATAR_DIR, env=env)


def wait_for_bridge(port: int | None = None, timeout: float = 25.0) -> bool:
    """Block until the avatar's local bridge accepts connections."""
    target = port or int(os.environ.get("PERSONA_BRIDGE_PORT", DEFAULT_BRIDGE_PORT))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with contextlib.suppress(OSError), socket.create_connection(("127.0.0.1", target), 0.4):
            return True
        time.sleep(0.25)
    return False


def _set_terminal_title(title: str) -> None:
    if not sys.stdout.isatty():
        return
    sys.stdout.write(f"\033]2;{title}\007")
    sys.stdout.flush()


def _wlrctl(action: str, marker: str) -> list[str]:
    result = subprocess.run(
        ["wlrctl", "toplevel", action, f"title:{marker}"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


@contextlib.contextmanager
def terminal_hidden(enabled: bool = True):
    """Minimize this terminal for the duration of the block, then bring it back."""
    marker = f"gillie-avatar-session-{os.getpid()}"
    if (
        not enabled
        or not sys.stdout.isatty()
        or not os.environ.get("WAYLAND_DISPLAY")
        or not shutil.which("wlrctl")
    ):
        yield False
        return

    _set_terminal_title(marker)
    time.sleep(0.35)

    try:
        matches = _wlrctl("list", marker)
    except (OSError, subprocess.SubprocessError):
        matches = []
    if len(matches) != 1:
        _set_terminal_title("gillie")
        yield False
        return

    restored = False

    def restore(*_args) -> None:
        nonlocal restored
        if restored:
            return
        restored = True
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            _wlrctl("activate", marker)
        _set_terminal_title("gillie")

    atexit.register(restore)
    previous_handlers = {}
    for sig in (signal.SIGTERM, signal.SIGHUP):
        with contextlib.suppress(ValueError, OSError):
            previous_handlers[sig] = signal.signal(sig, lambda s, f: (restore(), sys.exit(128 + s)))

    try:
        _wlrctl("minimize", marker)
        yield True
    finally:
        restore()
        for sig, handler in previous_handlers.items():
            with contextlib.suppress(ValueError, OSError):
                signal.signal(sig, handler)


@app.command("stop")
def stop():
    """Stop running Persona avatar processes."""
    killed = []
    for proc_path in Path("/proc").iterdir():
        if not proc_path.name.isdigit():
            continue
        try:
            cmdline = (proc_path / "cmdline").read_bytes().replace(b"\x00", b" ").decode(errors="replace")
            if str(AVATAR_DIR) in cmdline:
                pid = int(proc_path.name)
                os.kill(pid, signal.SIGTERM)
                killed.append(pid)
        except (PermissionError, FileNotFoundError, ProcessLookupError):
            continue

    if killed:
        console.print(f"[green]✓[/green] Stopped {len(killed)} avatar process(es).")
    else:
        console.print("[dim]No running avatar processes found.[/dim]")
