"""
Brain CLI commands

gillie brain edit        — enable/disable episodic memory, configure Qdrant
gillie brain status      — config + Qdrant connection + memory count
gillie brain stats       — memory distribution by importance, type, and age
gillie brain list        — recent episodic memories from MongoDB
gillie brain clear       — delete all episodic memories and soul knowledge
gillie brain consolidate — promote high-importance memories to the soul store (+ auto-prune)
gillie brain prune       — delete stale low-importance memories
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from InquirerPy import inquirer

from cli.config.manager import config_exists, load_config

console = Console()

app = typer.Typer(help="Manage episodic memory (brain).")


def _qdrant_collection_points(qc, collection_name: str):
    try:
        info = qc.get_collection(collection_name)
        return str(info.points_count or 0)
    except Exception:
        return "[dim]collection not yet created[/dim]"


def _require_config():
    if not config_exists():
        console.print("[red]✗[/red] No config found. Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)


def _require_brain(config):
    if not config.services.brain.enabled:
        console.print("[yellow]⚠[/yellow]  Brain is [bold]disabled[/bold].")
        console.print("  Enable it with [bold cyan]gillie brain edit[/bold cyan]")
        raise typer.Exit(0)


def _mongo_collection(config):
    from pymongo import MongoClient
    uri = config.services.mongodb.uri
    db_name = config.services.mongodb.database
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client, client[db_name]["episodic_memories"]


def _qdrant_client(config):
    from qdrant_client import QdrantClient
    return QdrantClient(
        host=config.services.qdrant.host,
        port=config.services.qdrant.port,
        api_key=config.services.qdrant.api_key,
        timeout=10,
    )


@app.command("edit")
def edit():
    """Edit brain (episodic memory) configuration."""
    from cli.config.manager import save_config
    _require_config()
    config = load_config()
    s = config.services

    console.print()
    s.brain.enabled = inquirer.confirm(
        "Enable episodic memory (brain)?", default=s.brain.enabled
    ).execute()

    if s.brain.enabled and not s.qdrant.enabled:
        console.print("[yellow]⚠[/yellow]  Brain requires Qdrant. Enabling Qdrant automatically.")
        s.qdrant.enabled = True
        s.qdrant.host = inquirer.text("Qdrant host", default=s.qdrant.host).execute()
        s.qdrant.port = int(inquirer.text("Qdrant port", default=str(s.qdrant.port)).execute())
        api_key = inquirer.text("Qdrant API key (optional)", default=s.qdrant.api_key or "").execute()
        s.qdrant.api_key = api_key or None

    save_config(config)
    console.print()
    console.print("✨🐙 [green]✓[/green] Brain configuration updated.")

    if s.brain.enabled:
        _inject_brain_skill()

    console.print()


def _inject_brain_skill() -> None:
    """Inject the brain knowledge block into rules.skill.md if not already present."""
    try:
        from src.core.platform.managers.skill_manager import (
            SkillManager, BRAIN_SKILL_MARKER, BRAIN_SKILL_BLOCK,
        )
        skill_manager = SkillManager()
        rules_content = skill_manager.load_skill("rules")

        if BRAIN_SKILL_MARKER in rules_content:
            console.print("[dim]  rules.skill.md already has the brain block — no changes.[/dim]")
            return

        skill_manager.save_skill("rules", rules_content.rstrip() + "\n" + BRAIN_SKILL_BLOCK)
        console.print("  [green]✓[/green] Brain block injected into [dim]rules.skill.md[/dim]")
    except Exception as e:
        console.print(f"  [yellow]⚠[/yellow]  Failed to inject brain block into rules.skill.md: {e}")


@app.command("stats")
def stats():
    """Show memory distribution by importance, type, and age."""
    _require_config()
    config = load_config()
    _require_brain(config)

    try:
        mongo_client, col = _mongo_collection(config)
        docs = list(col.find({"user_id": config.user_id}))
        mongo_client.close()
    except Exception as e:
        console.print(f"[red]✗[/red] MongoDB error: {e}")
        raise typer.Exit(1)

    if not docs:
        console.print("[dim]No episodic memories found.[/dim]")
        return

    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)

    total = len(docs)
    by_importance = {i: 0 for i in range(1, 11)}
    by_type: dict = {}
    age_7d = age_30d = age_90d = age_older = 0
    stale_candidates = 0
    soul_count = "-"

    for doc in docs:
        imp = doc.get("importance", 5)
        by_importance[imp] = by_importance.get(imp, 0) + 1

        mtype = doc.get("type", "episode")
        by_type[mtype] = by_type.get(mtype, 0) + 1

        created = doc.get("created_at")
        if created:
            age = (now - created.replace(tzinfo=timezone.utc) if created.tzinfo is None else now - created).days
            if age <= 7:
                age_7d += 1
            elif age <= 30:
                age_30d += 1
            elif age <= 90:
                age_90d += 1
            else:
                age_older += 1

            if imp <= 3 and age > 30:
                stale_candidates += 1
            elif imp <= 5 and age > 90 and doc.get("access_count", 0) == 0:
                stale_candidates += 1

    consolidate_candidates = sum(v for k, v in by_importance.items() if k >= 7)

    console.print()

    summary = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    summary.add_column("Key", style="bold dim")
    summary.add_column("Value")
    summary.add_row("Total memories", str(total))
    if config.services.qdrant.enabled:
        try:
            qc = _qdrant_client(config)
            soul_count = _qdrant_collection_points(qc, f"soul_{config.user_id}")
        except Exception as e:
            soul_count = f"[red]✗ {e}[/red]"
    summary.add_row("Soul knowledge", soul_count)
    summary.add_row("Consolidate candidates", f"[green]{consolidate_candidates}[/green] (importance >= 7)")
    summary.add_row("Prune candidates", f"[yellow]{stale_candidates}[/yellow] (stale low-importance)")
    console.print(summary)
    console.print()

    imp_table = Table(title="By Importance", box=box.SIMPLE, padding=(0, 1))
    imp_table.add_column("Importance", justify="center")
    imp_table.add_column("Count", justify="right")
    imp_table.add_column("Bar")
    max_count = max(by_importance.values()) or 1
    for imp in range(10, 0, -1):
        count = by_importance.get(imp, 0)
        if count == 0:
            continue
        bar_len = int((count / max_count) * 20)
        color = "green" if imp >= 7 else ("yellow" if imp >= 4 else "dim")
        imp_table.add_row(
            f"[{color}]{imp}[/{color}]",
            str(count),
            f"[{color}]{'█' * bar_len}[/{color}]",
        )
    console.print(imp_table)
    console.print()

    type_table = Table(title="By Type", box=box.SIMPLE, padding=(0, 1))
    type_table.add_column("Type")
    type_table.add_column("Count", justify="right")
    for mtype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        type_table.add_row(mtype, str(count))
    console.print(type_table)
    console.print()

    age_table = Table(title="By Age", box=box.SIMPLE, padding=(0, 1))
    age_table.add_column("Range")
    age_table.add_column("Count", justify="right")
    age_table.add_row("Last 7 days", str(age_7d))
    age_table.add_row("8–30 days", str(age_30d))
    age_table.add_row("31–90 days", str(age_90d))
    age_table.add_row("> 90 days", str(age_older))
    console.print(age_table)
    console.print()

    if consolidate_candidates > 0:
        console.print(f"[dim]Run [bold cyan]gillie brain consolidate[/bold cyan] to promote {consolidate_candidates} high-importance memories[/dim]")
    if stale_candidates > 0:
        console.print(f"[dim]Run [bold cyan]gillie brain prune[/bold cyan] to remove {stale_candidates} stale memories[/dim]")
    console.print()


@app.command("status")
def status():
    """Show brain config, Qdrant connection, and total memory count."""
    _require_config()
    config = load_config()
    _require_brain(config)

    console.print()

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold dim")
    table.add_column("Value")

    table.add_row("Brain", "[green]✓ enabled[/green]")

    qdrant_status = "[dim]not checked[/dim]"
    episodic_collection = f"episodic_{config.user_id}"
    soul_collection = f"soul_{config.user_id}"
    episodic_vectors = "-"
    soul_vectors = "-"

    if config.services.qdrant.enabled:
        try:
            qc = _qdrant_client(config)
            qc.get_collections()
            qdrant_status = f"[green]✓ connected[/green]  ({config.services.qdrant.host}:{config.services.qdrant.port})"

            episodic_vectors = _qdrant_collection_points(qc, episodic_collection)
            soul_vectors = _qdrant_collection_points(qc, soul_collection)
        except Exception as e:
            qdrant_status = f"[red]✗ unreachable[/red]  ({e})"
    else:
        qdrant_status = "[yellow]✗ disabled[/yellow]"

    table.add_row("Qdrant", qdrant_status)
    table.add_row("Episodic collection", episodic_collection)
    table.add_row("Episodic vectors", episodic_vectors)
    table.add_row("Soul collection", soul_collection)
    table.add_row("Soul vectors", soul_vectors)

    memory_count = "-"
    try:
        mongo_client, col = _mongo_collection(config)
        memory_count = str(col.count_documents({"user_id": config.user_id}))
        mongo_client.close()
    except Exception as e:
        memory_count = f"[red]✗ {e}[/red]"

    table.add_row("Episodic memories (MongoDB)", memory_count)

    console.print(table)
    console.print()


@app.command("list")
def list_memories(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of memories to show"),
    type_filter: str = typer.Option(None, "--type", "-t", help="Filter by type: episode, fact, preference, goal"),
):
    """List recent episodic memories from MongoDB."""
    _require_config()
    config = load_config()
    _require_brain(config)

    try:
        mongo_client, col = _mongo_collection(config)
        query = {"user_id": config.user_id}
        if type_filter:
            query["type"] = type_filter

        docs = list(col.find(query).sort("created_at", -1).limit(limit))
        mongo_client.close()
    except Exception as e:
        console.print(f"[red]✗[/red] MongoDB error: {e}")
        raise typer.Exit(1)

    if not docs:
        console.print("[dim]No episodic memories found.[/dim]")
        console.print(f"[dim]Start a conversation with the brain enabled to generate memories.[/dim]")
        return

    console.print()
    table = Table(
        title=f"Episodic Memories ({len(docs)} shown)",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("Date", style="dim", width=11)
    table.add_column("Type", width=10)
    table.add_column("Imp", justify="center", width=4)
    table.add_column("Emotion", width=11)
    table.add_column("Content")
    table.add_column("Tags", style="dim")

    for doc in docs:
        created = doc.get("created_at", "")
        if hasattr(created, "strftime"):
            date_str = created.strftime("%Y-%m-%d")
        else:
            date_str = str(created)[:10]

        importance = doc.get("importance", 5)
        imp_color = "green" if importance >= 7 else ("yellow" if importance >= 4 else "dim")
        imp_str = f"[{imp_color}]{importance}[/{imp_color}]"

        content = doc.get("content", "")
        if len(content) > 80:
            content = content[:77] + "..."

        tags = ", ".join(doc.get("tags", []))
        emotion = doc.get("emotion") or "[dim]—[/dim]"
        mem_type = doc.get("type", "episode")

        table.add_row(date_str, mem_type, imp_str, emotion, content, tags)

    console.print(table)
    console.print()


@app.command("clear")
def clear(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete all episodic memories and soul knowledge for the current user."""
    _require_config()
    config = load_config()
    _require_brain(config)

    if not yes:
        console.print(
            f"[red]⚠[/red]  This will delete [bold]all episodic memories and soul knowledge[/bold] "
            f"for user [bold]{config.user_id}[/bold]."
        )
        try:
            confirm = inquirer.select(
                message="Are you sure?",
                choices=[
                    {"name": "  No, cancel", "value": False},
                    {"name": "  Yes, delete all brain data", "value": True},
                ],
                pointer="❯", qmark="",
            ).execute()
        except KeyboardInterrupt:
            confirm = False
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    errors = []

    console.print()
    console.print("[bold]Clearing MongoDB episodic memories...[/bold]")
    try:
        mongo_client, col = _mongo_collection(config)
        result = col.delete_many({"user_id": config.user_id})
        mongo_client.close()
        console.print(f"  [green]✓[/green] Deleted [bold]{result.deleted_count}[/bold] memories")
    except Exception as e:
        msg = f"MongoDB clear failed: {e}"
        console.print(f"  [yellow]⚠[/yellow]  {msg}")
        errors.append(msg)

    console.print("[bold]Clearing Qdrant collections...[/bold]")
    if config.services.qdrant.enabled:
        collection_names = [
            f"episodic_{config.user_id}",
            f"soul_{config.user_id}",
        ]
        try:
            qc = _qdrant_client(config)
            collections = [c.name for c in qc.get_collections().collections]
            for collection_name in collection_names:
                if collection_name in collections:
                    qc.delete_collection(collection_name)
                    console.print(f"  [green]✓[/green] Collection [bold]{collection_name}[/bold] deleted")
                else:
                    console.print(f"  [dim]Collection {collection_name} not found — skipped[/dim]")
        except Exception as e:
            msg = f"Qdrant clear failed: {e}"
            console.print(f"  [yellow]⚠[/yellow]  {msg}")
            errors.append(msg)
    else:
        console.print("  [dim]Qdrant not enabled — skipped[/dim]")

    console.print()
    if errors:
        console.print(f"[yellow]Done with {len(errors)} warning(s).[/yellow]")
    else:
        console.print("[green]✓[/green] All brain data cleared.")
    console.print()


@app.command("consolidate")
def consolidate(
    min_importance: int = typer.Option(7, "--min-importance", "-i", help="Minimum importance threshold (1-10)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview memories without writing to soul"),
    no_prune: bool = typer.Option(False, "--no-prune", help="Skip automatic stale memory pruning after consolidation"),
):
    """Promote high-importance episodic memories to the soul store (soul molding)."""
    import asyncio
    _require_config()
    config = load_config()
    _require_brain(config)

    try:
        mongo_client, col = _mongo_collection(config)
        docs = list(col.find({
            "user_id": config.user_id,
            "importance": {"$gte": min_importance},
        }).sort("importance", -1))
        mongo_client.close()
    except Exception as e:
        console.print(f"[red]✗[/red] MongoDB error: {e}")
        raise typer.Exit(1)

    if not docs:
        console.print(f"[dim]No unconsolidated memories with importance >= {min_importance}.[/dim]")
        return

    console.print()
    console.print(f"Found [bold]{len(docs)}[/bold] memories to consolidate (importance >= {min_importance}):")
    console.print()

    table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
    table.add_column("Imp", justify="center", width=4)
    table.add_column("Type", width=10)
    table.add_column("Content")
    table.add_column("Tags", style="dim")

    for doc in docs:
        importance = doc.get("importance", 5)
        imp_color = "green" if importance >= 8 else "yellow"
        content = doc.get("content", "")
        if len(content) > 70:
            content = content[:67] + "..."
        tags = ", ".join(doc.get("tags", []))
        table.add_row(
            f"[{imp_color}]{importance}[/{imp_color}]",
            doc.get("type", "episode"),
            content,
            tags,
        )

    console.print(table)

    if dry_run:
        console.print("[dim]Dry run — no changes written.[/dim]")
        return

    # Use LLM to synthesize and write to the soul store
    from cli.config.manager import get_config_path
    import os
    os.environ["GILLIE_CONFIG"] = str(get_config_path())

    console.print()
    console.print("[bold]Synthesizing knowledge statements via LLM...[/bold]")

    try:
        from src.core.platform.config.service import init_config_from_json
        from src.adapters.web.integrations.openapi.openai_integration import OpenAIIntegration
        from src.core.platform.ai.embeddings.embedding_service import (
            EmbeddingService,
            create_huggingface_embeddings,
            create_openai_embeddings,
        )
        from src.core.platform.brain.episodic_vector_service import EpisodicVectorService
        from src.core.platform.brain.memory_consolidator import MemoryConsolidator
        from src.core.platform.brain.soul_vector_service import SoulVectorService

        svc_config = init_config_from_json(config)
        openai_integration = OpenAIIntegration(svc_config)
        emb_cfg = svc_config.embeddings_config

        if emb_cfg.provider == "openai":
            raw_embeddings = create_openai_embeddings(
                api_key=svc_config.openai_config.api_key,
                model=emb_cfg.openai_model,
            )
        else:
            raw_embeddings = create_huggingface_embeddings(
                model_name=emb_cfg.hf_model,
                device=emb_cfg.device,
            )

        embedding_service = EmbeddingService(raw_embeddings)

        class _SyncRepo:
            """Thin sync wrapper used only in CLI context."""
            def __init__(self, col, user_id, docs):
                self._col = col
                self._user_id = user_id
                self._docs = docs

            async def find_unconsolidated(self, user_id, min_importance=7):
                from src.core.domain.brain.episodic_memory import EpisodicMemory
                return [EpisodicMemory(**d) for d in self._docs]

            async def delete_many_by_ids(self, memory_ids):
                if not memory_ids:
                    return 0
                try:
                    mongo_client2, col2 = _mongo_collection(config)
                    result = col2.delete_many({"_id": {"$in": memory_ids}})
                    mongo_client2.close()
                    return result.deleted_count
                except Exception as exc:
                    console.print(f"  [yellow]⚠[/yellow]  Failed to delete promoted memories: {exc}")
                    return 0

            async def find_stale(self, user_id, max_importance, older_than_days, require_zero_access=False):
                from datetime import datetime, timedelta, timezone
                from src.core.domain.brain.episodic_memory import EpisodicMemory
                cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
                query = {
                    "user_id": user_id,
                    "importance": {"$lte": max_importance},
                    "created_at": {"$lt": cutoff},
                }
                if require_zero_access:
                    query["access_count"] = 0
                try:
                    mongo_client2, col2 = _mongo_collection(config)
                    docs = list(col2.find(query))
                    mongo_client2.close()
                    return [EpisodicMemory(**d) for d in docs]
                except Exception:
                    return []

        episodic_vector_service = None
        soul_vector_service = None
        if config.services.qdrant.enabled:
            try:
                from src.adapters.vectorstore.qdrant_adapter import QdrantVectorStoreAdapter
                qdrant_adapter = QdrantVectorStoreAdapter(svc_config, raw_embeddings)
                episodic_vector_service = EpisodicVectorService(qdrant_adapter, embedding_service)
                soul_vector_service = SoulVectorService(qdrant_adapter, embedding_service)
            except Exception:
                pass

        mongo_client3, col3 = _mongo_collection(config)
        repo = _SyncRepo(col3, config.user_id, docs)
        consolidator = MemoryConsolidator(
            repo,
            openai_integration,
            episodic_vector_service,
            soul_vector_service,
        )

        if soul_vector_service is None:
            console.print("[red]✗[/red] Soul store is not available. Configure Qdrant correctly before consolidating.")
            raise typer.Exit(1)

        result = asyncio.run(consolidator.consolidate(config.user_id, min_importance, auto_prune=not no_prune))
        mongo_client3.close()

        written = result.get("written", 0)
        pruned = result.get("pruned", 0)

        if written:
            console.print("  [green]✓[/green] Wrote [bold]%d[/bold] knowledge statement(s) to [dim]Qdrant soul store[/dim]" % written)
            console.print(f"  [green]✓[/green] Removed [bold]{len(docs)}[/bold] promoted memories from MongoDB + Qdrant")
        else:
            console.print("  [dim]No new statements written (all may already exist).[/dim]")

        if pruned:
            console.print(f"  [green]✓[/green] Pruned [bold]{pruned}[/bold] stale memories")

    except Exception as e:
        console.print(f"[red]✗[/red] Consolidation failed: {e}")
        raise typer.Exit(1)

    console.print()
    console.print("[green]✓[/green] Soul molding complete.")
    console.print()


@app.command("prune")
def prune(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview what would be deleted without deleting"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete stale low-importance memories (importance ≤ 3 older than 30d, importance ≤ 5 older than 90d with no access)."""
    _require_config()
    config = load_config()
    _require_brain(config)

    try:
        mongo_client, col = _mongo_collection(config)
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        cutoff_30 = now - timedelta(days=30)
        cutoff_90 = now - timedelta(days=90)

        # Rule 1: importance <= 3 older than 30 days
        rule1 = list(col.find({
            "user_id": config.user_id,
            "importance": {"$lte": 3},
            "created_at": {"$lt": cutoff_30},
        }))

        # Rule 2: importance <= 5, never accessed, older than 90 days
        rule2 = list(col.find({
            "user_id": config.user_id,
            "importance": {"$lte": 5},
            "created_at": {"$lt": cutoff_90},
            "access_count": 0,
        }))
        mongo_client.close()
    except Exception as e:
        console.print(f"[red]✗[/red] MongoDB error: {e}")
        raise typer.Exit(1)

    # Deduplicate by _id
    seen = set()
    candidates = []
    for doc in rule1 + rule2:
        doc_id = str(doc["_id"])
        if doc_id not in seen:
            seen.add(doc_id)
            candidates.append(doc)

    if not candidates:
        console.print("[dim]No stale memories found — nothing to prune.[/dim]")
        return

    console.print()
    console.print(f"Found [bold]{len(candidates)}[/bold] stale memories to prune:")
    console.print()

    table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
    table.add_column("Date", style="dim", width=11)
    table.add_column("Imp", justify="center", width=4)
    table.add_column("Access", justify="center", width=6)
    table.add_column("Content")

    for doc in candidates:
        created = doc.get("created_at", "")
        date_str = created.strftime("%Y-%m-%d") if hasattr(created, "strftime") else str(created)[:10]
        importance = doc.get("importance", 0)
        content = doc.get("content", "")
        if len(content) > 70:
            content = content[:67] + "..."
        table.add_row(date_str, str(importance), str(doc.get("access_count", 0)), content)

    console.print(table)

    if dry_run:
        console.print("[dim]Dry run — no changes made.[/dim]")
        return

    if not yes:
        try:
            confirm = inquirer.select(
                message=f"Delete {len(candidates)} stale memories?",
                choices=[
                    {"name": "  No, cancel", "value": False},
                    {"name": f"  Yes, delete {len(candidates)} memories", "value": True},
                ],
                pointer="❯", qmark="",
            ).execute()
        except KeyboardInterrupt:
            confirm = False
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    ids = [str(doc["_id"]) for doc in candidates]

    # Delete from MongoDB
    try:
        mongo_client2, col2 = _mongo_collection(config)
        result = col2.delete_many({"_id": {"$in": ids}})
        mongo_client2.close()
        console.print(f"  [green]✓[/green] Deleted [bold]{result.deleted_count}[/bold] memories from MongoDB")
    except Exception as e:
        console.print(f"  [yellow]⚠[/yellow]  MongoDB deletion failed: {e}")

    # Delete vectors from Qdrant
    if config.services.qdrant.enabled:
        try:
            qc = _qdrant_client(config)
            collection_name = f"episodic_{config.user_id}"
            collections = [c.name for c in qc.get_collections().collections]
            if collection_name in collections:
                from qdrant_client.http import models as qmodels
                conditions = [
                    qmodels.FieldCondition(
                        key="metadata.memory_id",
                        match=qmodels.MatchValue(value=mid),
                    )
                    for mid in ids
                ]
                qc.delete(
                    collection_name=collection_name,
                    points_selector=qmodels.FilterSelector(
                        filter=qmodels.Filter(should=conditions)
                    ),
                )
                console.print(f"  [green]✓[/green] Removed vectors from Qdrant")
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow]  Qdrant deletion failed: {e}")
    else:
        console.print("  [dim]Qdrant not enabled — skipped[/dim]")

    console.print()
    console.print("[green]✓[/green] Prune complete.")
    console.print()
