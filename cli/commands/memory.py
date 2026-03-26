"""
Memory CLI commands

gillie memory show
gillie memory edit
gillie memory extract
gillie memory faqs list
gillie memory faqs add
gillie memory faqs delete <id>
gillie memory skills list
gillie memory skills show <name>
gillie memory skills edit <name>
gillie memory skills rename <old> <new>
"""

import os
import subprocess
import tempfile
import typer
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from InquirerPy import inquirer
from InquirerPy import inquirer
from pathlib import Path

from cli.config.manager import config_exists, load_config

console = Console()

MEMORY_DIR = Path.home() / ".gillie" / "memory"

app = typer.Typer(help="Manage assistant memory (skills + FAQs).")
faqs_app = typer.Typer(help="Manage FAQs in faqs.skill.md.")
skills_app = typer.Typer(help="Manage .skill.md files (list, show, edit, rename).")

app.add_typer(faqs_app, name="faqs")
app.add_typer(skills_app, name="skills")


def _require_config():
    if not config_exists():
        console.print("[red]✗[/red] No config found. Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)


def _get_base_url() -> str:
    config = load_config()
    host = config.server.host or "127.0.0.1"
    port = config.server.port or 8000
    return f"http://{host}:{port}"


def _api_get(path: str):
    url = _get_base_url() + path
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("[red]✗[/red] Cannot connect to API. Is [bold cyan]gillie start[/bold cyan] running?")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]✗[/red] API error: {e.response.status_code} — {e.response.text}")
        raise typer.Exit(1)


def _api_post(path: str, data: dict):
    url = _get_base_url() + path
    try:
        resp = requests.post(url, json=data, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("[red]✗[/red] Cannot connect to API.")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]✗[/red] API error: {e.response.status_code} — {e.response.text}")
        raise typer.Exit(1)


def _api_put(path: str, data: dict):
    url = _get_base_url() + path
    try:
        resp = requests.put(url, json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("[red]✗[/red] Cannot connect to API.")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]✗[/red] API error: {e.response.status_code} — {e.response.text}")
        raise typer.Exit(1)


def _api_delete(path: str):
    url = _get_base_url() + path
    try:
        resp = requests.delete(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("[red]✗[/red] Cannot connect to API.")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]✗[/red] API error: {e.response.status_code} — {e.response.text}")
        raise typer.Exit(1)


# ─── FAQs commands ────────────────────────────────────────────────────────────

@faqs_app.command("list")
def faqs_list():
    """List all FAQs from faqs.skill.md."""
    _require_config()
    result = _api_get("/api/v1/memory/faqs")
    faqs = result.get("data", [])

    if not faqs:
        console.print("[dim]No FAQs found. Use [bold cyan]gillie memory faqs add[/bold cyan] to add one.[/dim]")
        return

    table = Table(title="FAQs", box=box.ROUNDED, border_style="cyan")
    table.add_column("ID", style="dim", width=10)
    table.add_column("Category", style="bold")
    table.add_column("Question")
    table.add_column("Answer")

    for faq in faqs:
        table.add_row(faq["id"], faq["category"], faq["question"], faq["answer"][:60] + "..." if len(faq["answer"]) > 60 else faq["answer"])

    console.print()
    console.print(table)
    console.print()


@faqs_app.command("add")
def faqs_add():
    """Add a new FAQ interactively."""
    _require_config()

    category = inquirer.text(
        message="Category (e.g. Horarios, Precios):",
        default="General",
    ).execute()

    question = inquirer.text(
        message="Question:",
    ).execute()

    answer = inquirer.text(
        message="Answer:",
    ).execute()

    if not question.strip() or not answer.strip():
        console.print("[red]✗[/red] Question and answer cannot be empty.")
        raise typer.Exit(1)

    result = _api_post("/api/v1/memory/faqs", {"question": question, "answer": answer, "category": category})
    faq = result.get("data", {})
    console.print(f"[green]✓[/green] FAQ added with ID: [bold]{faq.get('id')}[/bold]")


@faqs_app.command("delete")
def faqs_delete(faq_id: str = typer.Argument(..., help="FAQ ID to delete")):
    """Delete a FAQ by ID."""
    _require_config()
    result = _api_delete(f"/api/v1/memory/faqs/{faq_id}")
    if result.get("deleted"):
        console.print(f"[green]✓[/green] FAQ [bold]{faq_id}[/bold] deleted.")
    else:
        console.print(f"[red]✗[/red] FAQ [bold]{faq_id}[/bold] not found.")


# ─── Skills commands ──────────────────────────────────────────────────────────

@skills_app.command("list")
def skills_list():
    """List all .skill.md files in ~/.gillie/memory/."""
    _require_config()
    result = _api_get("/api/v1/memory/skills")
    skills = result.get("data", [])

    if not skills:
        console.print("[dim]No skills found in ~/.gillie/memory/[/dim]")
        return

    console.print()
    for s in skills:
        console.print(f"  [cyan]•[/cyan] {s['name']}.skill.md")
    console.print()


@skills_app.command("show")
def skills_show(name: str = typer.Argument(..., help="Skill name (without .skill.md)")):
    """Show content of a skill file."""
    _require_config()
    result = _api_get(f"/api/v1/memory/skills/{name}")
    content = result.get("content", "")

    if not content.strip():
        console.print(f"[dim]{name}.skill.md is empty.[/dim]")
        return

    console.print()
    console.print(Panel(content, title=f"[bold cyan]{name}.skill.md[/bold cyan]", border_style="cyan"))
    console.print()


@skills_app.command("edit")
def skills_edit(name: str = typer.Argument(..., help="Skill name (without .skill.md)")):
    """Create or edit a .skill.md file in $EDITOR (or nano)."""
    _require_config()

    skill_path = MEMORY_DIR / f"{name}.skill.md"
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    current_content = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""

    editor = os.environ.get("EDITOR", "nano")

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        prefix=f"gillie_skill_{name}_",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(current_content)
        tmp_path = tmp.name

    try:
        subprocess.run([editor, tmp_path], check=True)
        new_content = Path(tmp_path).read_text(encoding="utf-8")
    except subprocess.CalledProcessError:
        console.print("[red]✗[/red] Editor exited with an error.")
        raise typer.Exit(1)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if new_content == current_content:
        console.print("[yellow]•[/yellow] No changes made.")
        return

    skill_path.write_text(new_content, encoding="utf-8")
    action = "updated" if current_content else "created"
    console.print(f"[green]✓[/green] {name}.skill.md {action}.")

    # If new skill, remind user to reference it in memory.md
    if not current_content:
        console.print(
            f"[dim]Tip: add [bold]ver {name}.skill.md[/bold] in memory.md to include it in the AI context.[/dim]"
        )


@skills_app.command("delete")
def skills_delete(
    name: str = typer.Argument(..., help="Skill name (without .skill.md)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a .skill.md file and remove its reference from memory.md."""
    _require_config()

    skill_path = MEMORY_DIR / f"{name}.skill.md"

    if not skill_path.exists():
        console.print(f"[red]✗[/red] {name}.skill.md not found.")
        raise typer.Exit(1)

    if not yes:
        try:
            confirm = inquirer.select(
                message=f"Delete {name}.skill.md?",
                choices=[{"name": "  No, cancel", "value": False}, {"name": "  Yes, delete", "value": True}],
                pointer="❯", qmark="",
            ).execute()
        except KeyboardInterrupt:
            confirm = False
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    skill_path.unlink()
    console.print(f"[green]✓[/green] {name}.skill.md deleted.")

    # Remove reference from memory.md if present
    memory_path = MEMORY_DIR / "memory.md"
    if memory_path.exists():
        content = memory_path.read_text(encoding="utf-8")
        ref = f"ver {name}.skill.md"
        if ref in content:
            lines = [l for l in content.splitlines() if l.strip() != ref]
            memory_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            console.print(f"[green]✓[/green] Reference removed from memory.md.")


@skills_app.command("rename")
def skills_rename(
    old_name: str = typer.Argument(..., help="Current skill name (without .skill.md)"),
    new_name: str = typer.Argument(..., help="New skill name (without .skill.md)"),
):
    """Rename a .skill.md file and update references in memory.md."""
    _require_config()

    old_path = MEMORY_DIR / f"{old_name}.skill.md"
    new_path = MEMORY_DIR / f"{new_name}.skill.md"

    if not old_path.exists():
        console.print(f"[red]✗[/red] {old_name}.skill.md not found.")
        raise typer.Exit(1)

    if new_path.exists():
        console.print(f"[red]✗[/red] {new_name}.skill.md already exists.")
        raise typer.Exit(1)

    old_path.rename(new_path)
    console.print(f"[green]✓[/green] Renamed [bold]{old_name}.skill.md[/bold] → [bold]{new_name}.skill.md[/bold]")

    # Update references in memory.md
    memory_path = MEMORY_DIR / "memory.md"
    if memory_path.exists():
        content = memory_path.read_text(encoding="utf-8")
        old_ref = f"ver {old_name}.skill.md"
        new_ref = f"ver {new_name}.skill.md"
        if old_ref in content:
            content = content.replace(old_ref, new_ref)
            memory_path.write_text(content, encoding="utf-8")
            console.print(f"[green]✓[/green] Updated reference in memory.md")


# ─── Extract command ──────────────────────────────────────────────────────────

@app.command("extract")
def extract():
    """Run memory extraction: summarize conversations → update general.skill.md."""
    _require_config()
    console.print("[dim]Running memory extraction (this may take a moment)...[/dim]")
    result = _api_post("/api/v1/memory/extract", {})
    extracted = result.get("extracted", 0)
    status = result.get("status", "")

    if status == "no_new_conversations":
        console.print("[yellow]•[/yellow] No new conversations to extract.")
    else:
        console.print(f"[green]✓[/green] Extracted memory from [bold]{extracted}[/bold] conversation(s).")
        console.print(f"[dim]general.skill.md has been updated.[/dim]")


# ─── Show / Edit memory.md ────────────────────────────────────────────────────

@app.command("show")
def show():
    """Show raw memory.md content (the root of the skill tree)."""
    _require_config()
    result = _api_get("/api/v1/memory/root")
    content = result.get("content", "")

    console.print()
    if not content.strip():
        console.print("[dim]memory.md is empty. Start the API to auto-create it.[/dim]")
        console.print()
        return

    console.print(Panel(content, title="[bold cyan]memory.md[/bold cyan]", border_style="cyan"))

    # List skills referenced in memory.md
    import re
    refs = re.findall(r"^ver\s+([\w\-]+)\.skill\.md\s*$", content, re.MULTILINE)
    if refs:
        console.print()
        console.print("[bold]Referenced skills:[/bold]")
        for name in refs:
            skill_path = MEMORY_DIR / f"{name}.skill.md"
            exists = skill_path.exists()
            size = f"{skill_path.stat().st_size} bytes" if exists else "[dim]not found[/dim]"
            icon = "[green]✓[/green]" if exists else "[yellow]?[/yellow]"
            console.print(f"  {icon} {name}.skill.md  [dim]{size}[/dim]")

    console.print()


@app.command("edit")
def edit():
    """Open memory.md in $EDITOR (or nano) for interactive editing."""
    _require_config()

    # Fetch current content
    result = _api_get("/api/v1/memory/root")
    current_content = result.get("content", "")

    editor = os.environ.get("EDITOR", "nano")

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        prefix="gillie_memory_",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(current_content)
        tmp_path = tmp.name

    try:
        subprocess.run([editor, tmp_path], check=True)
        new_content = Path(tmp_path).read_text(encoding="utf-8")
    except subprocess.CalledProcessError:
        console.print(f"[red]✗[/red] Editor exited with an error.")
        raise typer.Exit(1)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if new_content == current_content:
        console.print("[yellow]•[/yellow] No changes made.")
        return

    _api_put("/api/v1/memory/root", {"content": new_content})
    console.print("[green]✓[/green] memory.md updated.")
