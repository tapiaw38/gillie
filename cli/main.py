import typer
from rich.console import Console

from cli.commands.init import app as init_app
from cli.commands.start import app as start_app
from cli.commands.soul import app as soul_app
from cli.commands.profile import app as profile_app
from cli.commands.services import app as services_app
from cli.commands.db import app as db_app
from cli.commands.qdrant import app as qdrant_app
from cli.commands.service import app as service_app
from cli.commands.memory import app as memory_app
from cli.commands.ui import app as ui_app

console = Console()

app = typer.Typer(
    name="gillie",
    help="✨🐟 [bold cyan]Gillie[/bold cyan] — Single-user AI assistant CLI",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(init_app, name="init", help="Interactive setup wizard")
app.add_typer(start_app, name="start", help="Start the API server")
app.add_typer(soul_app, name="soul", help="Manage assistant soul (identity + profile)")
app.add_typer(profile_app, name="profile", help="Manage profile configuration")
app.add_typer(services_app, name="services", help="Manage service configurations")
app.add_typer(db_app, name="db", help="Manage MongoDB database (Docker)")
app.add_typer(qdrant_app, name="qdrant", help="Manage Qdrant vector store (Docker)")
app.add_typer(service_app, name="service", help="Manage systemd service")
app.add_typer(memory_app, name="memory", help="Manage assistant memory (skills + FAQs)")
app.add_typer(ui_app, name="ui", help="Manage the Gillie UI (Vue dashboard)")


@app.command("status")
def status():
    """Show current configuration status."""
    from cli.config.manager import config_exists, load_config, get_config_path
    from rich.table import Table
    from rich import box

    if not config_exists():
        console.print("[red]✗[/red] Not initialized. Run [bold cyan]gillie init[/bold cyan]")
        raise typer.Exit(1)

    from cli.config.manager import get_soul_path
    config = load_config()
    s = config.services

    console.print()
    console.print(f"✨🐟 [bold cyan]Gillie[/bold cyan] — {config.profile.assistant_name}")
    console.print(f"[dim]Soul:   {get_soul_path()}[/dim]")
    console.print(f"[dim]Config: {get_config_path()}[/dim]")
    console.print()

    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("Key", style="bold dim")
    table.add_column("Value")

    table.add_row("User ID", config.user_id)
    table.add_row("Assistant", config.profile.assistant_name)
    table.add_row("Business", config.profile.business_name)
    table.add_row("Model", f"{s.openai.model}")
    table.add_row("MongoDB", s.mongodb.uri)
    table.add_row("Server", f"{config.server.host}:{config.server.port}")
    table.add_row("LangChain", "on" if s.langchain.enabled else "off")
    table.add_row("Qdrant", "on" if s.qdrant.enabled else "off")
    table.add_row("S3", "on" if s.s3.enabled else "off")
    table.add_row("TTS", "on" if s.tts.enabled else "off")
    table.add_row("STT", "on" if s.stt.enabled else "off")
    table.add_row("WhatsApp", "on" if s.whatsapp.enabled else "off")
    table.add_row("MercadoLibre", "on" if s.mercadolibre.enabled else "off")

    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
