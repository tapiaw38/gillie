"""
gillie build — hidden command to compile the project for distribution.

Targets:
  api   Compile the FastAPI backend with Cython → release/api/
  cli   Compile the CLI binary with Nuitka     → release/gillie
  ui    Build the Vue UI with Vite             → release/ui/
  all   Run all three (default)
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(hidden=True, help="Compile project for distribution")
console = Console()

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "release"


# ─── helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> int:
    result = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        env={**os.environ, **(env or {})},
    )
    return result.returncode


def _section(title: str) -> None:
    console.print()
    console.rule(f"[bold cyan]{title}[/bold cyan]")
    console.print()


# ─── API target ───────────────────────────────────────────────────────────────

# Deps that are optional / incompatible with Python 3.14 or too heavy to bundle.
# They use lazy imports in the codebase so excluding them only disables those
# optional features (WhatsApp/neonize, local HuggingFace embeddings, OpenCV).
_API_EXCLUDED_PACKAGES = [
    "neonize",
    "langchain_huggingface",
    "sentence_transformers",
    "torch",
    "torchvision",
    "torchaudio",
    "cv2",
    "sklearn",        # scikit-learn — optional, heavy
    "skimage",        # scikit-image — optional, heavy
    "matplotlib",
    "seaborn",
    "sounddevice",
    "webrtcvad",
    "playwright",
    "debugpy",
    "pytest",
    "mongomock",
]

def _build_api(out: Path) -> bool:
    _section("API — Nuitka compilation")

    out.mkdir(parents=True, exist_ok=True)

    nuitka = shutil.which("nuitka")
    if not nuitka:
        check = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True,
        )
        if check.returncode != 0:
            console.print("[red]✗ Nuitka not found.[/red] Install: [cyan]pip install nuitka[/cyan]")
            return False
        nuitka_cmd = [sys.executable, "-m", "nuitka"]
    else:
        nuitka_cmd = [nuitka]

    exclude_flags = [f"--nofollow-import-to={pkg}" for pkg in _API_EXCLUDED_PACKAGES]

    cmd = [
        *nuitka_cmd,
        "--standalone",
        "--onefile",
        "--output-filename=gillie-api",
        f"--output-dir={out}",
        "--follow-imports",
        # Core packages
        "--include-package=src",
        "--include-package=fastapi",
        "--include-package=uvicorn",
        "--include-package=pydantic",
        "--include-package=pymongo",
        "--include-package=openai",
        "--include-package=langchain",
        "--include-package=langchain_openai",
        "--include-package=langchain_community",
        "--include-package=langchain_qdrant",
        "--include-package=langgraph",
        "--include-package=boto3",
        "--include-package=botocore",
        "--include-package=dotenv",
        "--include-package=jwt",
        "--include-package=aiohttp",
        "--include-package=aiofiles",
        "--include-package=requests",
        "--include-package=pymupdf",
        "--include-package=pytesseract",
        "--include-package=PIL",
        "--include-package=qdrant_client",
        "--include-package=apscheduler",
        # Non-code data files needed at runtime
        "--include-data-dir=src=src",
        # Exclude heavy / optional / 3.14-incompatible deps
        *exclude_flags,
        "--python-flag=no_docstrings",
        "--python-flag=no_asserts",
        "main.py",
    ]

    console.print("[dim]Compiling API binary with Nuitka (this takes several minutes)...[/dim]")
    console.print(f"[dim]Excluding optional packages: {', '.join(_API_EXCLUDED_PACKAGES)}[/dim]")
    rc = _run(cmd, cwd=ROOT)

    if rc != 0:
        console.print("[red]✗ Nuitka compilation failed.[/red]")
        return False

    binary = out / "gillie-api"
    console.print(f"[green]✓ API binary compiled →[/green] {binary}")
    console.print("[dim]  Note: WhatsApp/neonize and local HuggingFace embeddings not included.[/dim]")
    console.print("[dim]  Requires: tesseract binary on PATH, MongoDB, Qdrant.[/dim]")
    return True


# ─── CLI target ───────────────────────────────────────────────────────────────

def _build_cli(out: Path) -> bool:
    _section("CLI — Nuitka compilation")

    out.mkdir(parents=True, exist_ok=True)

    nuitka = shutil.which("nuitka") or shutil.which("python3.nuitka")
    if not nuitka:
        check = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True,
        )
        if check.returncode != 0:
            console.print("[red]✗ Nuitka not found.[/red] Install it with: [cyan]pip install nuitka[/cyan]")
            return False
        nuitka_cmd = [sys.executable, "-m", "nuitka"]
    else:
        nuitka_cmd = [nuitka]

    binary_name = "gillie"
    cmd = [
        *nuitka_cmd,
        "--standalone",
        "--onefile",
        f"--output-filename={binary_name}",
        f"--output-dir={out}",
        "--follow-imports",
        "--include-package=cli",
        "--include-package=src.core.platform.config",
        "--include-package=rich",
        "--include-package=typer",
        "--include-package=InquirerPy",
        "--include-package=prompt_toolkit",
        "--include-package=requests",
        "--noinclude-setuptools-mode=nofollow",
        "--python-flag=no_docstrings",
        "--python-flag=no_asserts",
        "cli/main.py",
    ]

    console.print("[dim]Compiling CLI binary with Nuitka (this takes several minutes)...[/dim]")
    rc = _run(cmd, cwd=ROOT)

    if rc != 0:
        console.print("[red]✗ Nuitka compilation failed.[/red]")
        return False

    binary = out / binary_name
    console.print(f"[green]✓ CLI binary compiled →[/green] {binary}")
    return True


# ─── UI target ────────────────────────────────────────────────────────────────

def _build_ui(out: Path) -> bool:
    _section("UI — Electron build")

    ui_dir = ROOT / "ui"
    if not ui_dir.exists():
        console.print("[yellow]⚠ ui/ directory not found, skipping.[/yellow]")
        return True

    console.print("[dim]Running npm run electron:build...[/dim]")
    rc = _run(["npm", "run", "electron:build"], cwd=ui_dir)

    if rc != 0:
        console.print("[red]✗ Electron build failed.[/red]")
        return False

    if not out.exists():
        console.print("[red]✗ Build output not found.[/red]")
        return False

    installers = [
        f for f in out.rglob("*")
        if f.is_file() and f.suffix in (".AppImage", ".deb", ".dmg", ".exe", ".rpm")
    ]
    for installer in installers:
        console.print(f"  [cyan]→[/cyan] {installer.name}")

    console.print(f"[green]✓ UI built →[/green] {out}")
    return True


# ─── command ──────────────────────────────────────────────────────────────────

@app.command("run", hidden=True)
def build_run(
    target: str = typer.Argument("all", help="api | cli | ui | all"),
):
    """Compile project for distribution."""
    targets = ["api", "cli", "ui"] if target == "all" else [target]

    valid = {"api", "cli", "ui", "all"}
    if target not in valid:
        console.print(f"[red]Unknown target:[/red] {target}")
        console.print(f"[dim]Valid: {', '.join(sorted(valid))}[/dim]")
        raise typer.Exit(1)

    RELEASE.mkdir(parents=True, exist_ok=True)
    results: dict[str, bool] = {}

    for t in targets:
        if t == "api":
            results["api"] = _build_api(RELEASE / "api")
        elif t == "cli":
            results["cli"] = _build_cli(RELEASE / "cli")
        elif t == "ui":
            results["ui"] = _build_ui(RELEASE / "ui")

    console.print()
    console.rule("[bold]Build summary[/bold]")
    all_ok = True
    for t, ok in results.items():
        icon = "[green]✓[/green]" if ok else "[red]✗[/red]"
        path = RELEASE / t
        console.print(f"  {icon}  [bold]{t}[/bold]  →  [dim]{path}[/dim]")
        if not ok:
            all_ok = False
    console.print()

    if not all_ok:
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def build_callback(
    ctx: typer.Context,
    target: str = typer.Argument("all", help="api | cli | ui | all"),
):
    if ctx.invoked_subcommand is None:
        build_run(target)
