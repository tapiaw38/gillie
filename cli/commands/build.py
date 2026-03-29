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

def _build_api(out: Path) -> bool:
    _section("API — compile to optimized bytecode (.pyc)")

    out.mkdir(parents=True, exist_ok=True)

    src_root = ROOT / "src"

    py_files = [
        f for f in src_root.rglob("*.py")
        if "__pycache__" not in f.parts and "test" not in f.parts
    ]
    console.print(f"[dim]Found {len(py_files)} Python files[/dim]")

    console.print("[dim]Compiling to optimised bytecode (-OO)...[/dim]")
    rc = _run(
        [sys.executable, "-OO", "-m", "compileall", "-b", "-q", str(src_root)],
        cwd=ROOT,
    )
    if rc != 0:
        console.print("[red]✗ compileall failed.[/red]")
        return False

    compiled = list(src_root.rglob("*.pyc"))
    console.print(f"[green]✓ Compiled {len(compiled)} files[/green]")

    console.print("[dim]Copying bytecode to release/api/...[/dim]")
    for pyc in compiled:
        # pyc lands next to the .py when using -b flag
        dest = out / pyc.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pyc, dest)
        pyc.unlink()  # remove .pyc from source tree

    for f in src_root.rglob("*"):
        if f.is_file() and f.suffix not in (".py", ".pyc") and "__pycache__" not in f.parts:
            dest = out / f.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)

    keep_as_is = [
        "main.py", "requirements.txt", "Dockerfile",
        "docker-compose.mongo.yml", "docker-compose.qdrant.yml",
        "init-mongo.js",
    ]
    for name in keep_as_is:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, out / name)

    console.print(f"[green]✓ API ready →[/green] {out}")
    console.print("[dim]  Distribute release/api/ — no .py source files included[/dim]")
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
