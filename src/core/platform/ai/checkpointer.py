"""Durable LangGraph checkpoints backed by Gillie's existing MongoDB."""
from __future__ import annotations

from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient


def mongo_checkpointer(config_service, *, ttl_seconds: int = 86_400) -> MongoDBSaver:
    """Create saver in a separate database; never mixes graph state with chats."""
    conversations = config_service.nosql_config.conversations
    if conversations is None:
        raise RuntimeError("Mongo conversation configuration is required for agent checkpoints")
    client = MongoClient(
        conversations.database_uri,
        connectTimeoutMS=5_000,
        serverSelectionTimeoutMS=5_000,
    )
    return MongoDBSaver(
        client,
        db_name=f"{conversations.database}_langgraph",
        checkpoint_collection_name="checkpoints",
        writes_collection_name="writes",
        ttl=ttl_seconds,
    )
