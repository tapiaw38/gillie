import typer
from rich.console import Console

from cli.commands.config import app as config_app
from cli.commands.init import app as init_app
from cli.commands.start import app as start_app
from cli.commands.profile import app as profile_app
from cli.commands.services import app as services_app
from cli.commands.db import app as db_app
from cli.commands.qdrant import app as qdrant_app
from cli.commands.service import app as service_app
from cli.commands.memory import app as memory_app
from cli.commands.ui import app as ui_app
from cli.commands.tunnel import app as tunnel_app
from cli.commands.expose import app as expose_app
from cli.commands.install import app as install_app
from cli.commands.agent import app as agent_app
from cli.commands.reset import app as reset_app
from cli.commands.provider import app as provider_app
from cli.commands.brain import app as brain_app
from cli.commands.build import app as build_app

console = Console()

app = typer.Typer(
    name="gillie",
    help="✨🐙 [bold cyan]Gillie[/bold cyan] — Single-user AI assistant CLI",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(init_app, name="init", help="Interactive setup wizard")
app.add_typer(start_app, name="start", help="Start the API server")
app.add_typer(config_app, name="config", help="Manage assistant identity and profile")
app.add_typer(profile_app, name="profile", help="Manage profile configuration")
app.add_typer(services_app, name="services", help="Manage service configurations")
app.add_typer(db_app, name="db", help="Manage MongoDB database (Docker)")
app.add_typer(qdrant_app, name="qdrant", help="Manage Qdrant vector store (Docker)")
app.add_typer(service_app, name="service", help="Manage systemd service")
app.add_typer(memory_app, name="memory", help="Manage assistant memory (skills + FAQs)")
app.add_typer(ui_app, name="ui", help="Manage the Gillie UI (Vue dashboard)")
app.add_typer(tunnel_app, name="tunnel", help="SSH tunnel to a remote VPS")
app.add_typer(expose_app, name="expose", help="Expose API via nginx (HTTP/HTTPS)")
app.add_typer(install_app, name="install", help="Install Python dependencies")
app.add_typer(agent_app, name="agent", help="Interactive chat with the assistant")
app.add_typer(reset_app, name="reset", help="Reset Gillie to factory state")
app.add_typer(brain_app, name="brain", help="Manage episodic memory (brain)")
app.add_typer(provider_app, name="provider", help="Manage AI provider (DeepSeek, OpenRouter, Claude, etc.)")
app.add_typer(build_app, name="build", hidden=True)


@app.command("status")
def status():
    """Show current configuration status."""
    from cli.config.manager import config_exists, load_config, get_config_path
    from rich.table import Table
    from rich import box

    if not config_exists():
        console.print("[red]✗[/red] Not initialized. Run [bold cyan]gillie init[/bold cyan]")
        raise typer.Exit(1)

    config = load_config()
    s = config.services

    console.print()
    console.print(f"✨🐙 [bold cyan]Gillie[/bold cyan] — {config.profile.assistant_name}")
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
    table.add_row("Brain", "on" if s.brain.enabled else "off")
    table.add_row("S3", "on" if s.s3.enabled else "off")
    table.add_row("TTS", "on" if s.tts.enabled else "off")
    table.add_row("STT", "on" if s.stt.enabled else "off")
    table.add_row("WhatsApp", "on" if s.whatsapp.enabled else "off")
    table.add_row("MercadoLibre", "on" if s.mercadolibre.enabled else "off")

    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
