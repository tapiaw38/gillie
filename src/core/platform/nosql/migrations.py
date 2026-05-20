from datetime import datetime, timezone
from typing import Awaitable, Callable, List, Any
from uuid import uuid4


class Migration:
    def __init__(self, version: int, up: Callable[[Any], Awaitable[Any]]):
        self.version = version
        self.up = up


def execute_migrations() -> List[Migration]:
    async def add_is_active(db):
        return await db["profiles"].update_many(
            {},
            {"$set": {"is_active": True}}
        )

    async def add_iteration_limit(db):
        return await db["profiles"].update_many(
            {},
            {"$set": {"iteration_limit": 100}}
        )

    async def add_files(db):
        return await db["profiles"].update_many(
            {},
            {"$set": {"files": []}}
        )

    async def add_client_id(db):
        return await db["conversations"].update_many(
            {},
            {"$set": {"client_id": str(uuid4())}}
        )

    async def add_role(db):
        return await db["profiles"].update_many(
            {},
            {"$set": {"role": "seller"}}
        )

    async def add_is_sandbox(db):
        return await db["conversations"].update_many(
            {"is_sandbox": {"$exists": False}},
            {"$set": {"is_sandbox": False}}
        )

    async def add_faq_profile_id(db):
        return await db["faqs"].update_many(
            {"profile_id": {"$exists": False}},
            {"$set": {"profile_id": None}}
        )

    async def add_tts_enabled(db):
        return await db["profiles"].update_many(
            {"tts_enabled": {"$exists": False}},
            {"$set": {"tts_enabled": False}}
        )

    async def backfill_episodic_memory_created_at(db):
        return await db["episodic_memories"].update_many(
            {"created_at": {"$exists": False}},
            {"$set": {"created_at": datetime.now(timezone.utc)}}
        )

    async def remove_business_name(db):
        return await db["profiles"].update_many(
            {"business_name": {"$exists": True}},
            {"$unset": {"business_name": ""}}
        )

    return [
        Migration(
            version=1,
            up=add_is_active,
        ),
        Migration(
            version=2,
            up=add_iteration_limit,
        ),
        Migration(
            version=3,
            up=add_files,
        ),
        Migration(
            version=4,
            up=add_client_id,
        ),
        Migration(
            version=5,
            up=add_role,
        ),
        Migration(
            version=6,
            up=add_is_sandbox,
        ),
        Migration(
            version=7,
            up=add_faq_profile_id,
        ),
        Migration(
            version=8,
            up=add_tts_enabled,
        ),
        Migration(
            version=9,
            up=backfill_episodic_memory_created_at,
        ),
        Migration(
            version=10,
            up=remove_business_name,
        ),
    ]
