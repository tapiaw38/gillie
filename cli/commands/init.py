import uuid
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from InquirerPy import inquirer
from InquirerPy.validator import EmptyInputValidator

from cli.config.schema import (
    AssistantConfig,
    ProfileConfig,
    ServerConfig,
    ServicesConfig,
    MongoDBConfig,
    OpenAIServiceConfig,
    LangChainServiceConfig,
    QdrantServiceConfig,
    EmbeddingsServiceConfig,
    S3ServiceConfig,
    TTSServiceConfig,
    STTServiceConfig,
    WhatsAppServiceConfig,
    MercadoLibreServiceConfig,
    LangSmithServiceConfig,
    LLMExtendedServiceConfig,
    LoggingConfig,
)
from cli.config.manager import save_config, config_exists, get_config_path, get_soul_path

console = Console()

app = typer.Typer()


def _prompt_text(message: str, default: str = "", required: bool = False) -> str:
    validator = EmptyInputValidator(f"{message} is required") if required else None
    result = inquirer.text(
        message=message,
        default=default,
        validate=validator,
    ).execute()
    return result or default


def _prompt_confirm(message: str, default: bool = False) -> bool:
    return inquirer.confirm(message=message, default=default).execute()


def _prompt_select(message: str, choices: list, default: str = None) -> str:
    return inquirer.select(
        message=message,
        choices=choices,
        default=default or choices[0],
    ).execute()


def _prompt_password(message: str) -> str:
    return inquirer.secret(
        message=message,
        validate=EmptyInputValidator(f"{message} is required"),
    ).execute()


@app.callback(invoke_without_command=True)
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
):
    """Interactive setup wizard for Gillie."""
    console.print()
    console.print(Panel(
        "✨🐟 [bold cyan]Gillie[/bold cyan] — Setup Wizard",
        subtitle="Single-user AI assistant",
        border_style="cyan",
    ))
    console.print()

    # Check existing config
    if config_exists() and not force:
        console.print(f"[yellow]Config already exists at {get_config_path()}[/yellow]")
        overwrite = _prompt_confirm("Overwrite existing configuration?", default=False)
        if not overwrite:
            console.print("[dim]Setup cancelled.[/dim]")
            raise typer.Exit(0)

    console.print("[bold]Assistant Profile[/bold]")
    console.print("[dim]Configure your AI assistant's identity[/dim]")
    console.print()

    assistant_name = _prompt_text("Assistant name", required=True)
    business_name = _prompt_text("Business name", required=True)
    business_context = _prompt_text("Business context (optional)", default="")
    functions = _prompt_text("Functions / tools description (optional)", default="")

    console.print()
    console.print("[bold]Database (MongoDB)[/bold]")
    mongo_choice = _prompt_select(
        "MongoDB setup",
        choices=["Docker (local, recommended)", "External instance"],
        default="Docker (local, recommended)",
    )

    if "Docker" in mongo_choice:
        mongodb_uri = "mongodb://localhost:27017"
        mongodb_mode = "docker"
        mongodb_db = _prompt_text("Database name", default="gillie-db")
        console.print("  [dim]Run [bold cyan]./gillie db start[/bold cyan] to start MongoDB[/dim]")
    else:
        mongodb_uri = _prompt_text("MongoDB URI", required=True)
        mongodb_db = _prompt_text("Database name", default="gillie-db")
        mongodb_mode = "external"

    console.print()
    console.print("[bold]AI Provider[/bold]")
    openai_key = _prompt_password("API key (OpenAI / DeepSeek / compatible)")
    openai_base_url = _prompt_text("Base URL", default="https://api.deepseek.com")
    openai_model = _prompt_text("Model name", default="deepseek-chat")
    openai_temperature = float(_prompt_text("Temperature", default="0.7"))
    openai_max_tokens = int(_prompt_text("Max tokens", default="2000"))

    console.print()
    console.print("[bold]LangChain / RAG[/bold]")
    enable_langchain = _prompt_confirm("Enable LangChain service?", default=False)
    langchain_cfg = LangChainServiceConfig(enabled=enable_langchain)

    enable_qdrant = False
    qdrant_cfg = QdrantServiceConfig(enabled=False)
    if enable_langchain:
        vector_store = _prompt_select(
            "Vector store backend",
            choices=["faiss", "qdrant"],
            default="faiss",
        )
        langchain_cfg.vector_store = vector_store
        if vector_store == "qdrant":
            enable_qdrant = True
            qdrant_host = _prompt_text("Qdrant host", default="localhost")
            qdrant_port = int(_prompt_text("Qdrant port", default="6333"))
            qdrant_api_key = _prompt_text("Qdrant API key (optional)", default="")
            qdrant_cfg = QdrantServiceConfig(
                enabled=True,
                host=qdrant_host,
                port=qdrant_port,
                api_key=qdrant_api_key or None,
            )

    embeddings_provider = "huggingface"
    embeddings_cfg = EmbeddingsServiceConfig(provider="huggingface")
    if enable_langchain:
        console.print()
        console.print("[bold]Embeddings[/bold]")
        embeddings_provider = _prompt_select(
            "Embeddings provider",
            choices=["huggingface", "openai"],
            default="huggingface",
        )
        embeddings_cfg = EmbeddingsServiceConfig(provider=embeddings_provider)
        if embeddings_provider == "huggingface":
            embeddings_cfg.hf_model = _prompt_text(
                "HuggingFace model",
                default="sentence-transformers/all-MiniLM-L6-v2",
            )

    console.print()
    console.print("[bold]File Storage (S3)[/bold]")
    enable_s3 = _prompt_confirm("Enable S3 file storage?", default=False)
    s3_cfg = S3ServiceConfig(enabled=False)
    if enable_s3:
        s3_cfg = S3ServiceConfig(
            enabled=True,
            access_key_id=_prompt_text("AWS Access Key ID", required=True),
            secret_access_key=_prompt_password("AWS Secret Access Key"),
            region=_prompt_text("AWS Region", default="us-east-1"),
            bucket_name=_prompt_text("S3 Bucket Name", required=True),
        )

    console.print()
    console.print("[bold]Audio[/bold]")
    enable_tts = _prompt_confirm("Enable Text-to-Speech (TTS)?", default=False)
    enable_stt = _prompt_confirm("Enable Speech-to-Text (STT)?", default=False)

    console.print()
    console.print("[bold]WhatsApp Integration[/bold]")
    enable_whatsapp = _prompt_confirm("Enable WhatsApp webhook?", default=False)
    whatsapp_cfg = WhatsAppServiceConfig(enabled=False)
    if enable_whatsapp:
        verify_token = _prompt_text("WhatsApp verify token", required=True)
        whatsapp_cfg = WhatsAppServiceConfig(enabled=True, verify_token=verify_token)

    console.print()
    console.print("[bold]MercadoLibre Integration[/bold]")
    enable_ml = _prompt_confirm("Enable MercadoLibre integration?", default=False)

    console.print()
    console.print("[bold]Observability (LangSmith)[/bold]")
    enable_langsmith = _prompt_confirm("Enable LangSmith tracing?", default=False)
    langsmith_cfg = LangSmithServiceConfig(enabled=False)
    if enable_langsmith:
        langsmith_cfg = LangSmithServiceConfig(
            enabled=True,
            api_key=_prompt_password("LangSmith API key"),
            project=_prompt_text("LangSmith project", default="gillie-api"),
        )

    console.print()
    console.print("[bold]Server[/bold]")
    server_host = _prompt_text("Host", default="0.0.0.0")
    server_port = int(_prompt_text("Port", default="8000"))
    log_level = _prompt_select("Log level", choices=["INFO", "DEBUG", "WARNING", "ERROR"], default="INFO")

    # Build config
    config = AssistantConfig(
        user_id=str(uuid.uuid4()),
        profile=ProfileConfig(
            assistant_name=assistant_name,
            business_name=business_name,
            business_context=business_context,
            functions=functions,
        ),
        server=ServerConfig(host=server_host, port=server_port),
        services=ServicesConfig(
            mongodb=MongoDBConfig(uri=mongodb_uri, database=mongodb_db, mode=mongodb_mode),
            openai=OpenAIServiceConfig(
                api_key=openai_key,
                base_url=openai_base_url,
                model=openai_model,
                temperature=openai_temperature,
                max_tokens=openai_max_tokens,
            ),
            langchain=langchain_cfg,
            qdrant=qdrant_cfg,
            embeddings=embeddings_cfg,
            s3=s3_cfg,
            tts=TTSServiceConfig(enabled=enable_tts),
            stt=STTServiceConfig(enabled=enable_stt),
            whatsapp=whatsapp_cfg,
            mercadolibre=MercadoLibreServiceConfig(enabled=enable_ml),
            langsmith=langsmith_cfg,
            llm=LLMExtendedServiceConfig(),
        ),
        logging=LoggingConfig(log_level=log_level),
    )

    save_config(config)

    console.print()
    _print_summary(config)
    console.print()
    console.print(f"✨🐟 [green]✓[/green] Soul saved to   [bold]{get_soul_path()}[/bold]")
    console.print(f"   [green]✓[/green] Config saved to [bold]{get_config_path()}[/bold]")
    console.print()
    console.print(f"Start the server with: [bold cyan]./gillie start[/bold cyan]")
    console.print()


def _print_summary(config: AssistantConfig) -> None:
    table = Table(title="Configuration Summary", box=box.ROUNDED, border_style="cyan")
    table.add_column("Setting", style="bold")
    table.add_column("Value")

    table.add_row("User ID", config.user_id)
    table.add_row("Assistant name", config.profile.assistant_name)
    table.add_row("Business name", config.profile.business_name)
    table.add_row("MongoDB", config.services.mongodb.uri)
    table.add_row("AI model", f"{config.services.openai.model} ({config.services.openai.base_url})")
    table.add_row("LangChain", "✓ enabled" if config.services.langchain.enabled else "✗ disabled")
    table.add_row("Qdrant", "✓ enabled" if config.services.qdrant.enabled else "✗ disabled")
    table.add_row("S3 storage", "✓ enabled" if config.services.s3.enabled else "✗ disabled")
    table.add_row("TTS", "✓ enabled" if config.services.tts.enabled else "✗ disabled")
    table.add_row("STT", "✓ enabled" if config.services.stt.enabled else "✗ disabled")
    table.add_row("WhatsApp", "✓ enabled" if config.services.whatsapp.enabled else "✗ disabled")
    table.add_row("MercadoLibre", "✓ enabled" if config.services.mercadolibre.enabled else "✗ disabled")
    table.add_row("LangSmith", "✓ enabled" if config.services.langsmith.enabled else "✗ disabled")
    table.add_row("Server", f"{config.server.host}:{config.server.port}")

    console.print(table)
