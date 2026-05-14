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


def _venv_nuitka_cmd() -> list[str]:
    """Return the preferred Nuitka invocation for this project.

    Avoids the system nuitka shim (#!/usr/bin/python) picking up the wrong
    site-packages and failing to locate venv-only packages, while preserving
    fallback to the active interpreter or PATH when the project venv exists
    but does not have Nuitka installed.
    """
    candidates: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    def add_candidate(cmd: list[str]) -> None:
        key = tuple(cmd)
        if key not in seen:
            seen.add(key)
            candidates.append(cmd)

    venv_python = ROOT / ".venv" / "bin" / "python3"
    if venv_python.exists():
        add_candidate([str(venv_python), "-m", "nuitka"])

    add_candidate([sys.executable, "-m", "nuitka"])

    nuitka_bin = shutil.which("nuitka")
    if nuitka_bin:
        add_candidate([nuitka_bin])

    for cmd in candidates:
        check = subprocess.run(cmd + ["--version"], capture_output=True)
        if check.returncode == 0:
            return cmd

    return candidates[0] if candidates else [sys.executable, "-m", "nuitka"]



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

    nuitka_cmd = _venv_nuitka_cmd()
    if subprocess.run(nuitka_cmd + ["--version"], capture_output=True).returncode != 0:
        console.print("[red]✗ Nuitka not found.[/red] Install: [cyan]pip install nuitka[/cyan]")
        return False

    exclude_flags = [f"--nofollow-import-to={pkg}" for pkg in _API_EXCLUDED_PACKAGES]

    cmd = [
        *nuitka_cmd,
        "--standalone",
        "--onefile",
        "--output-filename=gillie-api",
        f"--output-dir={out}",
        "--follow-imports",

        # ── Core app ──────────────────────────────────────────────────────────
        "--include-package=src",

        # ── Web framework ─────────────────────────────────────────────────────
        "--include-package=fastapi",
        "--include-package=starlette",       # fastapi base
        "--include-package=uvicorn",
        "--include-package=anyio",           # uvicorn/starlette async
        "--include-package=click",           # uvicorn CLI
        "--include-package=multipart",       # fastapi file uploads
        "--include-package=pydantic",
        "--include-package=aiohttp",
        "--include-package=aiofiles",
        "--include-package=httpx",           # openai client transport

        # ── Database / storage ────────────────────────────────────────────────
        "--include-package=pymongo",
        "--include-package=boto3",
        "--include-package=botocore",

        # ── AI / LLM ──────────────────────────────────────────────────────────
        "--include-package=openai",
        "--include-package=anthropic",
        "--include-package=tiktoken",        # openai tokenizer
        "--include-package=langchain",
        "--include-package=langchain_core",
        "--include-package=langchain_openai",
        "--include-package=langchain_anthropic",
        "--include-package=langchain_ollama",
        "--include-package=langchain_community",
        "--include-package=langchain_qdrant",
        "--include-package=langchain_text_splitters",
        "--include-package=langgraph",
        "--include-package=langsmith",

        # ── Vector store ──────────────────────────────────────────────────────
        "--include-package=qdrant_client",
        "--include-package=faiss",
        "--include-package=numpy",

        # ── Document processing ───────────────────────────────────────────────
        "--include-package=PIL",
        "--include-package=pytesseract",
        "--include-package=pymupdf",         # fitz
        "--include-package=PyPDF2",
        "--include-package=pdf2image",
        "--include-package=docx",            # python-docx
        "--include-package=pptx",            # python-pptx
        "--include-package=openpyxl",
        "--include-package=pandas",

        # ── Google integrations ───────────────────────────────────────────────
        "--include-package=google",
        "--include-package=google_auth_oauthlib",
        "--include-package=googleapiclient",

        # ── Audio / TTS / STT ─────────────────────────────────────────────────
        "--include-package=gtts",
        "--include-package=pydub",
        "--include-package=speech_recognition",

        # ── Utilities ─────────────────────────────────────────────────────────
        "--include-package=requests",
        "--include-package=dotenv",
        "--include-package=jwt",
        "--include-package=apscheduler",
        "--include-package=dateparser",
        "--include-package=qrcode",
        "--include-package=duckduckgo_search",

        # ── Distribution metadata (packages that self-inspect their version) ──
        "--include-distribution-metadata=langchain",
        "--include-distribution-metadata=langchain-core",
        "--include-distribution-metadata=langchain-openai",
        "--include-distribution-metadata=langchain-community",
        "--include-distribution-metadata=openai",
        "--include-distribution-metadata=fastapi",
        "--include-distribution-metadata=pydantic",

        "--include-data-dir=src=src",
        *exclude_flags,
        "--noinclude-setuptools-mode=nofollow",
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



def _build_cli(out: Path) -> bool:
    _section("CLI — Nuitka compilation")

    out.mkdir(parents=True, exist_ok=True)

    nuitka_cmd = _venv_nuitka_cmd()
    if subprocess.run(nuitka_cmd + ["--version"], capture_output=True).returncode != 0:
        console.print("[red]✗ Nuitka not found.[/red] Install it with: [cyan]pip install nuitka[/cyan]")
        return False

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
