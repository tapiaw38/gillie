"""
Agent CLI — Interactive chat with the Gillie assistant from the terminal.

Usage:
  gillie agent                  # start or resume the CLI conversation
  gillie agent --new            # force a new conversation
  gillie agent --id <conv_id>   # attach to a specific conversation

In-chat commands:
  /new     — start a new conversation
  /clear   — delete all messages in current conversation
  /id      — show current conversation ID
  /exit    — quit (also Ctrl+C or Ctrl+D)
"""

import sys
import typer
import requests
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule
from rich import box
from rich.text import Text

from cli.config.manager import config_exists, load_config

console = Console()
app = typer.Typer()

_CLI_CONV_TITLE = "CLI Agent"


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _base_url() -> str:
    config = load_config()
    host = config.server.host or "127.0.0.1"
    if host == "0.0.0.0":
        host = "127.0.0.1"
    port = config.server.port or 8000
    return f"http://{host}:{port}"


def _get(path: str) -> dict:
    try:
        resp = requests.get(_base_url() + path, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("\n[red]✗[/red] No se puede conectar a la API. ¿Está corriendo [bold cyan]gillie start[/bold cyan]?")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}")
        raise typer.Exit(1)


def _post_json(path: str, data: dict) -> dict:
    try:
        resp = requests.post(_base_url() + path, json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("\n[red]✗[/red] No se puede conectar a la API.")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}")
        raise typer.Exit(1)


def _post_form(path: str, content: str) -> dict:
    try:
        resp = requests.post(
            _base_url() + path,
            data={"content": content},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("\n[red]✗[/red] No se puede conectar a la API.")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}")
        return {}


def _delete(path: str) -> dict:
    try:
        resp = requests.delete(_base_url() + path, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("\n[red]✗[/red] No se puede conectar a la API.")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}")
        return {}


# ─── Conversation helpers ──────────────────────────────────────────────────────

def _find_cli_conversation() -> dict | None:
    """Return the existing CLI Agent conversation, or None."""
    result = _get("/conversation/user")
    conversations = result.get("data", [])
    for conv in conversations:
        if conv.get("title") == _CLI_CONV_TITLE:
            return conv
    return None


def _create_conversation() -> dict:
    """Create a new CLI Agent conversation."""
    result = _post_json("/conversation/", {"title": _CLI_CONV_TITLE})
    return result.get("data", result)


def _send_message(conv_id: str, content: str) -> str:
    """Send a message and return the assistant's reply text."""
    result = _post_form(f"/conversation/{conv_id}/message", content)
    messages = result.get("data", [])
    if not messages:
        return "(sin respuesta)"
    # Last message is the assistant's reply
    last = messages[-1]
    return last.get("content", "(sin respuesta)")


def _clear_messages(conv_id: str) -> None:
    _delete(f"/conversation/{conv_id}/message")


# ─── Display helpers ───────────────────────────────────────────────────────────

def _print_header(assistant_name: str, conv_id: str) -> None:
    console.print()
    console.print(Panel(
        f"✨🐟 [bold cyan]{assistant_name}[/bold cyan]\n"
        f"[dim]Conversación: {conv_id}[/dim]\n"
        f"[dim]/new · /list · /clear · /id · /exit[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
    ))
    console.print()


def _print_user(text: str) -> None:
    console.print(f"[bold white]Vos[/bold white]  [dim]{text}[/dim]")


def _print_assistant(name: str, text: str) -> None:
    console.print()
    try:
        console.print(Panel(
            Markdown(text),
            title=f"[bold cyan]{name}[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 1),
        ))
    except Exception:
        console.print(Panel(text, title=f"[bold cyan]{name}[/bold cyan]", border_style="cyan"))
    console.print()


def _print_history(messages: list, assistant_name: str) -> None:
    """Print the last few messages so the user has context on resume."""
    if not messages:
        return
    recent = messages[-6:]  # last 3 exchanges
    console.print(Rule("[dim]historial reciente[/dim]", style="dim"))
    for msg in recent:
        sender = msg.get("sender", "")
        content = msg.get("content", "")
        if sender == "user":
            _print_user(content)
        else:
            _print_assistant(assistant_name, content)
    console.print(Rule(style="dim"))
    console.print()


# ─── Main command ──────────────────────────────────────────────────────────────

@app.command("list")
def list_conversations():
    """Listar todas las conversaciones con su ID y título."""
    if not config_exists():
        console.print("[red]✗[/red] No hay configuración. Ejecutá [bold cyan]gillie init[/bold cyan] primero.")
        raise typer.Exit(1)

    from rich.table import Table
    from rich import box as rbox

    result = _get("/conversation/user")
    conversations = result.get("data", [])

    if not conversations:
        console.print("[dim]No hay conversaciones. Iniciá una con [bold cyan]gillie agent[/bold cyan].[/dim]")
        return

    table = Table(box=rbox.ROUNDED, border_style="cyan", show_lines=False)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Título", style="bold")
    table.add_column("Mensajes", justify="right")
    table.add_column("Última actividad", style="dim")

    for conv in conversations:
        cid = conv.get("id") or conv.get("_id", "")
        title = conv.get("title") or "[dim]sin título[/dim]"
        msgs = len(conv.get("messages", []))
        updated = (conv.get("updated_at") or conv.get("created_at") or "")[:19].replace("T", " ")
        table.add_row(cid, title, str(msgs), updated)

    console.print()
    console.print(table)
    console.print()
    console.print(f"[dim]Conectate a una conversación: [bold cyan]gillie agent --id <ID>[/bold cyan][/dim]")
    console.print()


@app.callback(invoke_without_command=True)
def agent(
    new: bool = typer.Option(False, "--new", "-n", help="Forzar nueva conversación"),
    conv_id: str = typer.Option(None, "--id", help="ID de conversación específica"),
):
    """Chat interactivo con el asistente desde la terminal."""
    if not config_exists():
        console.print("[red]✗[/red] No hay configuración. Ejecutá [bold cyan]gillie init[/bold cyan] primero.")
        raise typer.Exit(1)

    config = load_config()
    assistant_name = config.profile.assistant_name

    # ── resolve conversation ──────────────────────────────────────────────────
    if conv_id:
        result = _get(f"/conversation/{conv_id}")
        conversation = result.get("data", result)
    elif new:
        conversation = _create_conversation()
        console.print(f"[green]✓[/green] Nueva conversación creada.")
    else:
        conversation = _find_cli_conversation()
        if conversation is None:
            conversation = _create_conversation()
            console.print(f"[green]✓[/green] Nueva conversación CLI creada.")

    current_id = conversation.get("id") or conversation.get("_id")
    if not current_id:
        console.print("[red]✗[/red] No se pudo obtener el ID de la conversación.")
        raise typer.Exit(1)

    _print_header(assistant_name, current_id)

    # Show recent history if resuming
    messages = conversation.get("messages", [])
    if messages:
        _print_history(messages, assistant_name)

    # ── REPL ─────────────────────────────────────────────────────────────────
    console.print(f"[dim]Escribí tu mensaje y presioná Enter. /exit para salir.[/dim]")
    console.print()

    while True:
        try:
            user_input = console.input("[bold cyan]Vos ›[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Hasta luego 👋[/dim]")
            break

        if not user_input:
            continue

        # ── in-chat commands ────────────────────────────────────────────────
        if user_input.lower() in ("/exit", "/quit", "/q"):
            console.print("[dim]Hasta luego 👋[/dim]")
            break

        if user_input.lower() == "/id":
            console.print(f"[dim]Conversación ID: [bold]{current_id}[/bold][/dim]\n")
            continue

        if user_input.lower() == "/list":
            from rich.table import Table
            from rich import box as rbox
            result = _get("/conversation/user")
            convs = result.get("data", [])
            table = Table(box=rbox.SIMPLE, border_style="dim", show_lines=False)
            table.add_column("ID", style="dim", no_wrap=True)
            table.add_column("Título", style="bold")
            table.add_column("Msgs", justify="right")
            for c in convs:
                cid = c.get("id") or c.get("_id", "")
                marker = " [cyan]◀ actual[/cyan]" if cid == current_id else ""
                table.add_row(cid, (c.get("title") or "sin título") + marker, str(len(c.get("messages", []))))
            console.print()
            console.print(table)
            console.print()
            continue

        if user_input.lower() == "/new":
            conversation = _create_conversation()
            current_id = conversation.get("id") or conversation.get("_id")
            console.print(f"[green]✓[/green] Nueva conversación: [bold]{current_id}[/bold]\n")
            _print_header(assistant_name, current_id)
            continue

        if user_input.lower() == "/clear":
            _clear_messages(current_id)
            console.print("[green]✓[/green] Mensajes borrados.\n")
            continue

        # ── send message ────────────────────────────────────────────────────
        _print_user(user_input)
        with console.status("[dim]Pensando...[/dim]", spinner="dots"):
            reply = _send_message(current_id, user_input)

        _print_assistant(assistant_name, reply)
