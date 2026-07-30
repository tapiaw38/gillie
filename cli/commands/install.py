import sys
import subprocess
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich import box

app = typer.Typer(help="Install Python dependencies")
console = Console()

_SYSTEM_DEPS = [
    {
        "package": "portaudio",
        "purpose": "Voice listen mode (sounddevice backend)",
        "required": True,
        "apt": "portaudio19-dev",
        "pacman": "portaudio",
        "brew": "portaudio",
        "check_bin": None,
    },
    {
        "package": "mpv",
        "purpose": "Audio playback for TTS responses in CLI",
        "required": False,
        "apt": "mpv",
        "pacman": "mpv",
        "brew": "mpv",
        "check_bin": "mpv",
    },
    {
        "package": "ffmpeg",
        "purpose": "Audio playback fallback (ffplay) for TTS responses",
        "required": False,
        "apt": "ffmpeg",
        "pacman": "ffmpeg",
        "brew": "ffmpeg",
        "check_bin": "ffplay",
    },
    {
        "package": "wlrctl",
        "purpose": "Hide the terminal while the avatar is on screen — wlroots Wayland only (gillie agent listen --avatar)",
        "required": False,
        "apt": "wlrctl",
        "pacman": "wlrctl",
        "brew": None,
        "check_bin": "wlrctl",
    },
    {
        "package": "tesseract",
        "purpose": "OCR for scanned PDF processing",
        "required": False,
        "apt": "tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng",
        "pacman": "tesseract tesseract-data-spa tesseract-data-eng",
        "brew": "tesseract",
        "check_bin": "tesseract",
    },
    {
        "package": "scrot",
        "purpose": "Desktop screenshot capture — X11 (take_screenshot tool)",
        "required": False,
        "apt": "scrot",
        "pacman": "scrot",
        "brew": "scrot",
        "check_bin": "scrot",
    },
    {
        "package": "grim",
        "purpose": "Desktop screenshot capture — Wayland (take_screenshot tool)",
        "required": False,
        "apt": "grim",
        "pacman": "grim",
        "brew": None,
        "check_bin": "grim",
    },
    {
        "package": "playwright-chromium",
        "purpose": "Browser automation — Chrome/Chromium engine (browser tool)",
        "required": False,
        "apt": None,
        "pacman": None,
        "brew": None,
        "check_bin": None,
        "post_install": "python -m playwright install chromium",
        "_cache_glob": "chromium*",
    },
    {
        "package": "playwright-firefox",
        "purpose": "Browser automation — Firefox engine, uses your real Firefox profile (browser tool)",
        "required": False,
        "apt": None,
        "pacman": None,
        "brew": None,
        "check_bin": None,
        "post_install": "python -m playwright install firefox",
        "_cache_glob": "firefox*",
    },
]


def _detect_package_manager() -> str | None:
    for pm in ("pacman", "apt", "brew"):
        if shutil.which(pm):
            return pm
    return None


def _check_installed(dep: dict) -> bool:
    if dep.get("check_bin"):
        return shutil.which(dep["check_bin"]) is not None
    if dep.get("_cache_glob"):
        cache = Path.home() / ".cache" / "ms-playwright"
        return any(cache.glob(dep["_cache_glob"])) if cache.exists() else False
    return True  # can't check, assume ok


def _resolve_pip() -> list[str]:
    """
    Return a pip invocation that will actually work.

    Priority:
    1. Already inside a venv → use current interpreter
    2. Project .venv exists → use its pip
    3. Not in a venv on a PEP-668 system → create .venv first, then use it
    """
    import venv as _venv

    project_root = Path(__file__).parents[2]
    venv_dir = project_root / ".venv"
    pip_bin = venv_dir / "bin" / "pip"

    if sys.prefix != sys.base_prefix:
        return [sys.executable, "-m", "pip"]

    if pip_bin.exists():
        return [str(pip_bin)]

    probe = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--dry-run", "--quiet", "pip"],
        capture_output=True,
    )
    if probe.returncode == 0:
        return [sys.executable, "-m", "pip"]

    console.print("[yellow]⚠[/yellow]  System pip is externally managed (PEP 668).")
    console.print(f"[cyan]Creating[/cyan] virtual environment at [bold]{venv_dir}[/bold]...")
    _venv.create(str(venv_dir), with_pip=True, clear=False)
    console.print(f"[green]✓[/green] venv created. Activate it anytime with: [bold]source {venv_dir}/bin/activate[/bold]")
    return [str(pip_bin)]


@app.callback(invoke_without_command=True)
def install(
    package: str = typer.Argument(None, help="Optional: install a specific package instead of requirements.txt"),
    upgrade: bool = typer.Option(False, "--upgrade", "-U", help="Upgrade all Python packages"),
    system: bool = typer.Option(False, "--system", "-s", help="Show and install system dependencies"),
):
    """
    Install dependencies from requirements.txt or a specific package.

    Examples:

      gillie install               # installs all requirements.txt
      gillie install asyncpg       # installs a single package
      gillie install -U            # upgrades all requirements
      gillie install --system      # installs system packages (portaudio, mpv, etc.)
    """
    if system:
        _install_system_deps()
        return

    pip = _resolve_pip() + ["install"]
    if upgrade:
        pip.append("--upgrade")

    if package:
        console.print(f"[cyan]Installing[/cyan] [bold]{package}[/bold]...")
        cmd = pip + [package]
    else:
        req_file = Path(__file__).parents[2] / "requirements.txt"
        if not req_file.exists():
            console.print(f"[red]✗[/red] requirements.txt not found at {req_file}")
            raise typer.Exit(1)
        console.print(f"[cyan]Installing[/cyan] from [bold]{req_file}[/bold]...")
        cmd = pip + ["-r", str(req_file)]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        console.print("[green]✓[/green] Done.")
        if not package:
            console.print(
                "Run [bold cyan]gillie provider use[/bold cyan] to configure your AI provider."
            )
    else:
        console.print("[red]✗[/red] Installation failed.")
        raise typer.Exit(result.returncode)


def _install_system_deps():
    pm = _detect_package_manager()

    table = Table(box=box.ROUNDED, border_style="cyan", show_lines=False)
    table.add_column("Package", style="bold")
    table.add_column("Purpose")
    table.add_column("Required")
    table.add_column("Post-install", style="dim")
    table.add_column("Status")

    for dep in _SYSTEM_DEPS:
        installed = _check_installed(dep)
        status = "[green]✓ installed[/green]" if installed else "[yellow]✗ missing[/yellow]"
        req = "[red]required[/red]" if dep["required"] else "[dim]optional[/dim]"
        post = dep.get("post_install", "")
        table.add_row(dep["package"], dep["purpose"], req, post, status)

    console.print()
    console.print(table)
    console.print()

    missing = [d for d in _SYSTEM_DEPS if not _check_installed(d)]
    if not missing:
        console.print("[green]✓[/green] All system dependencies are installed.")
        return

    if not pm:
        console.print("[yellow]⚠[/yellow] Could not detect package manager. Install manually:")
        for dep in missing:
            post = f"  → [dim]{dep['post_install']}[/dim]" if dep.get("post_install") else ""
            console.print(f"  [dim]•[/dim] [bold]{dep['package']}[/bold] — {dep['purpose']}{post}")
        return

    console.print(f"[dim]Detected package manager: [bold]{pm}[/bold][/dim]")

    packages = " ".join(dep[pm] for dep in missing if dep.get(pm))
    if not packages:
        return

    if pm == "pacman":
        cmd = ["sudo", "pacman", "-S", "--noconfirm"] + packages.split()
    elif pm == "apt":
        cmd = ["sudo", "apt", "install", "-y"] + packages.split()
    elif pm == "brew":
        cmd = ["brew", "install"] + packages.split()
    else:
        return

    console.print(f"[cyan]Running:[/cyan] {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        console.print("[green]✓[/green] System dependencies installed.")
    else:
        console.print("[red]✗[/red] Some packages failed to install.")

    for dep in missing:
        post = dep.get("post_install")
        if post:
            console.print(f"[cyan]Post-install:[/cyan] {post}")
            subprocess.run(post.split())
