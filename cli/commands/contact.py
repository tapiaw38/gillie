import typer
import requests
from urllib.parse import urlencode
from rich.console import Console
from rich.table import Table
from rich import box

from cli.config.manager import config_exists, load_config

console = Console()
app = typer.Typer(help="Manage contacts and contact memories.")


def _require_config() -> None:
    if not config_exists():
        console.print("[red]x[/red] No config found. Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)


def _base_url() -> str:
    config = load_config()
    host = config.server.host or "127.0.0.1"
    if host == "0.0.0.0":
        host = "127.0.0.1"
    port = config.server.port or 8000
    return f"http://{host}:{port}"


def _get(path: str) -> dict:
    try:
        resp = requests.get(_base_url() + path, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("[red]x[/red] Cannot connect to API. Is [bold cyan]gillie start[/bold cyan] running?")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]x[/red] API error {e.response.status_code}: {e.response.text}")
        raise typer.Exit(1)


def _post(path: str, payload: dict) -> dict:
    try:
        resp = requests.post(_base_url() + path, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("[red]x[/red] Cannot connect to API. Is [bold cyan]gillie start[/bold cyan] running?")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]x[/red] API error {e.response.status_code}: {e.response.text}")
        raise typer.Exit(1)


@app.command("list")
def list_contacts() -> None:
    """List contacts from the assistant profile."""
    _require_config()
    contacts = _get("/profile/contacts").get("data", [])
    if not contacts:
        console.print("[dim]No contacts found.[/dim]")
        return

    table = Table(box=box.SIMPLE, border_style="dim")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Channel")
    table.add_column("External ID", style="dim")
    for c in contacts:
        table.add_row(c.get("id", ""), c.get("name", ""), c.get("channel") or "general", c.get("external_id") or "-")
    console.print()
    console.print(table)
    console.print()


@app.command("add")
def add_contact(
    name: str = typer.Argument(..., help="Contact display name"),
    channel: str = typer.Option("", "--channel", "-c", help="Channel, e.g. whatsapp, telegram, email"),
    external_id: str = typer.Option("", "--external-id", "-e", help="External identifier on source platform"),
) -> None:
    """Create a contact."""
    _require_config()
    created = _post(
        "/profile/contacts",
        {
            "name": name,
            "channel": channel or None,
            "external_id": external_id or None,
        },
    ).get("data", {})
    console.print(f"[green]✓[/green] Contact created: [bold]{created.get('name', name)}[/bold] ([dim]{created.get('id', '')}[/dim])")


@app.command("memories")
def list_memories(
    contact_id: str = typer.Option("", "--contact-id", "-c", help="Filter by contact id"),
    query: str = typer.Option("", "--query", "-q", help="Search in memory content"),
    limit: int = typer.Option(20, "--limit", "-l", min=1, max=100, help="Page size"),
    offset: int = typer.Option(0, "--offset", "-o", min=0, help="Pagination offset"),
) -> None:
    """List owner memories with optional filters and pagination."""
    _require_config()
    params = {"limit": limit, "offset": offset}
    if contact_id:
        params["contact_id"] = contact_id
    if query:
        params["query"] = query
    result = _get("/api/v1/memory/owner/episodes?" + urlencode(params))
    rows = result.get("data", [])
    if not rows:
        console.print("[dim]No memories found for current filters.[/dim]")
        return

    table = Table(box=box.SIMPLE, border_style="dim")
    table.add_column("Created", style="dim")
    table.add_column("Scope", style="cyan")
    table.add_column("Importance", justify="right")
    table.add_column("Content")
    for m in rows:
        table.add_row(
            str(m.get("created_at", ""))[:19],
            m.get("memory_scope_id") or "-",
            str(m.get("importance", "")),
            m.get("content", ""),
        )
    console.print()
    console.print(table)
    next_offset = result.get("next_offset")
    if result.get("has_more") and next_offset is not None:
        console.print(f"[dim]More results available. Next offset: {next_offset}[/dim]")
    console.print()
