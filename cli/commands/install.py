import sys
import subprocess
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Install Python dependencies")
console = Console()


@app.callback(invoke_without_command=True)
def install(
    package: str = typer.Argument(None, help="Optional: install a specific package instead of requirements.txt"),
    upgrade: bool = typer.Option(False, "--upgrade", "-U", help="Upgrade packages"),
):
    """
    Install dependencies from requirements.txt or a specific package.

    Examples:

      gillie install               # installs all requirements.txt
      gillie install asyncpg       # installs a single package
      gillie install -U            # upgrades all requirements
    """
    pip = [sys.executable, "-m", "pip", "install"]

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
    else:
        console.print("[red]✗[/red] Installation failed.")
        raise typer.Exit(result.returncode)
