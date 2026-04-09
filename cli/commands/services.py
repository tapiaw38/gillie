import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from InquirerPy import inquirer

from cli.config.manager import load_config, save_config, config_exists

console = Console()

app = typer.Typer(help="Manage service configurations.")

SERVICE_NAMES = [
    "mongodb",
    "openai",
    "langchain",
    "qdrant",
    "embeddings",
    "s3",
    "tts",
    "stt",
    "whatsapp",
    "mercadolibre",
    "langsmith",
    "llm",
]


def _require_config():
    if not config_exists():
        console.print("[red]✗[/red] No config found. Run [bold cyan]./gillie init[/bold cyan] first.")
        raise typer.Exit(1)


def _status(enabled: bool) -> str:
    return "[green]✓ enabled[/green]" if enabled else "[dim]✗ disabled[/dim]"


@app.command("show")
def show():
    """Show the status of all configured services."""
    _require_config()
    config = load_config()
    s = config.services

    table = Table(title="✨🐙 Services Configuration", box=box.ROUNDED, border_style="cyan")
    table.add_column("Service", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    table.add_row("mongodb", "[green]✓ always on[/green]", s.mongodb.uri)
    table.add_row(
        "openai",
        "[green]✓ always on[/green]",
        f"{s.openai.model} @ {s.openai.base_url}",
    )
    table.add_row("langchain", _status(s.langchain.enabled), f"vector_store={s.langchain.vector_store}" if s.langchain.enabled else "")
    table.add_row("qdrant", _status(s.qdrant.enabled), f"{s.qdrant.host}:{s.qdrant.port}" if s.qdrant.enabled else "")
    table.add_row("embeddings", "[green]✓ always on[/green]", f"provider={s.embeddings.provider}")
    table.add_row("s3", _status(s.s3.enabled), f"bucket={s.s3.bucket_name}" if s.s3.enabled else "")
    table.add_row("tts", _status(s.tts.enabled), "")
    table.add_row("stt", _status(s.stt.enabled), "")
    table.add_row("whatsapp", _status(s.whatsapp.enabled), "verify_token set" if s.whatsapp.verify_token else "")
    table.add_row("mercadolibre", _status(s.mercadolibre.enabled), "")
    table.add_row("langsmith", _status(s.langsmith.enabled), f"project={s.langsmith.project}" if s.langsmith.enabled else "")

    console.print()
    console.print(table)
    console.print()


@app.command("edit")
def edit(
    service: str = typer.Argument(None, help="Service name to edit (mongodb, openai, langchain, ...)"),
):
    """Edit a specific service configuration interactively."""
    _require_config()
    config = load_config()

    if service is None:
        service = inquirer.select(
            message="Select service to edit",
            choices=SERVICE_NAMES,
        ).execute()

    if service not in SERVICE_NAMES:
        console.print(f"[red]Unknown service:[/red] {service}")
        console.print(f"Available: {', '.join(SERVICE_NAMES)}")
        raise typer.Exit(1)

    console.print()
    console.print(Panel(f"[bold]Edit service:[/bold] {service}", border_style="cyan"))
    console.print()

    s = config.services

    if service == "mongodb":
        s.mongodb.uri = inquirer.text("MongoDB URI", default=s.mongodb.uri).execute()
        s.mongodb.database = inquirer.text("Database name", default=s.mongodb.database).execute()

    elif service == "openai":
        s.openai.api_key = inquirer.secret("API key", validate=lambda x: len(x) > 0 or "Required").execute() or s.openai.api_key
        s.openai.base_url = inquirer.text("Base URL", default=s.openai.base_url).execute()
        s.openai.model = inquirer.text("Model", default=s.openai.model).execute()
        s.openai.temperature = float(inquirer.text("Temperature", default=str(s.openai.temperature)).execute())
        s.openai.max_tokens = int(inquirer.text("Max tokens", default=str(s.openai.max_tokens)).execute())
        s.openai.timeout = float(inquirer.text("Timeout (seconds)", default=str(s.openai.timeout)).execute())

    elif service == "langchain":
        s.langchain.enabled = inquirer.confirm("Enable LangChain?", default=s.langchain.enabled).execute()
        if s.langchain.enabled:
            s.langchain.vector_store = inquirer.select(
                "Vector store", choices=["faiss", "qdrant"], default=s.langchain.vector_store
            ).execute()
            s.langchain.chunk_size = int(inquirer.text("Chunk size", default=str(s.langchain.chunk_size)).execute())
            s.langchain.chunk_overlap = int(inquirer.text("Chunk overlap", default=str(s.langchain.chunk_overlap)).execute())
            s.langchain.similarity_k = int(inquirer.text("Similarity k", default=str(s.langchain.similarity_k)).execute())

    elif service == "qdrant":
        s.qdrant.enabled = inquirer.confirm("Enable Qdrant?", default=s.qdrant.enabled).execute()
        if s.qdrant.enabled:
            s.qdrant.host = inquirer.text("Host", default=s.qdrant.host).execute()
            s.qdrant.port = int(inquirer.text("Port", default=str(s.qdrant.port)).execute())
            api_key = inquirer.text("API key (optional)", default=s.qdrant.api_key or "").execute()
            s.qdrant.api_key = api_key or None

    elif service == "embeddings":
        s.embeddings.provider = inquirer.select(
            "Provider", choices=["huggingface", "openai"], default=s.embeddings.provider
        ).execute()
        s.embeddings.device = inquirer.select(
            "Device", choices=["cpu", "cuda", "mps"], default=s.embeddings.device
        ).execute()
        if s.embeddings.provider == "huggingface":
            s.embeddings.hf_model = inquirer.text("HuggingFace model", default=s.embeddings.hf_model).execute()

    elif service == "s3":
        s.s3.enabled = inquirer.confirm("Enable S3?", default=s.s3.enabled).execute()
        if s.s3.enabled:
            s.s3.access_key_id = inquirer.text("Access Key ID", default=s.s3.access_key_id).execute()
            s.s3.secret_access_key = inquirer.secret("Secret Access Key").execute() or s.s3.secret_access_key
            s.s3.region = inquirer.text("Region", default=s.s3.region).execute()
            s.s3.bucket_name = inquirer.text("Bucket name", default=s.s3.bucket_name).execute()

    elif service == "tts":
        s.tts.enabled = inquirer.confirm("Enable TTS?", default=s.tts.enabled).execute()

    elif service == "stt":
        s.stt.enabled = inquirer.confirm("Enable STT?", default=s.stt.enabled).execute()

    elif service == "whatsapp":
        s.whatsapp.enabled = inquirer.confirm("Enable WhatsApp?", default=s.whatsapp.enabled).execute()
        if s.whatsapp.enabled:
            s.whatsapp.verify_token = inquirer.text("Verify token", default=s.whatsapp.verify_token).execute()

    elif service == "mercadolibre":
        s.mercadolibre.enabled = inquirer.confirm("Enable MercadoLibre?", default=s.mercadolibre.enabled).execute()

    elif service == "langsmith":
        s.langsmith.enabled = inquirer.confirm("Enable LangSmith?", default=s.langsmith.enabled).execute()
        if s.langsmith.enabled:
            s.langsmith.api_key = inquirer.secret("API key").execute() or s.langsmith.api_key
            s.langsmith.project = inquirer.text("Project", default=s.langsmith.project).execute()

    elif service == "llm":
        s.llm.provider = inquirer.select(
            "LLM provider", choices=["openai", "anthropic"], default=s.llm.provider
        ).execute()
        if s.llm.provider == "anthropic":
            s.llm.anthropic_api_key = inquirer.secret("Anthropic API key").execute() or s.llm.anthropic_api_key
            s.llm.anthropic_model = inquirer.text("Anthropic model", default=s.llm.anthropic_model).execute()

    save_config(config)
    console.print()
    console.print(f"✨🐙 [green]✓[/green] Service [bold]{service}[/bold] updated.")
    console.print()
