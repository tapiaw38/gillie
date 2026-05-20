import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from bson import ObjectId
from pymongo.errors import PyMongoError

from src.adapters.datasources.datasources import Datasources
from src.core.domain.brain import EpisodicMemory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import DatabaseQueryError as CommonDatabaseQueryError
from .repository_interface import RepositoryInterface

logger = logging.getLogger(__name__)


def _normalize_document_id(document: dict) -> dict:
    normalized = dict(document)
    if "_id" in normalized and normalized["_id"] is not None:
        normalized["_id"] = str(normalized["_id"])
    return normalized


def _build_id_candidates(memory_id: str) -> list:
    candidates = [memory_id]
    if ObjectId.is_valid(memory_id):
        candidates.append(ObjectId(memory_id))
    return candidates


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.client = datasources.no_sql_episodic_memories_client

    async def create(self, memory: EpisodicMemory) -> str:
        try:
            memory_dict = memory.dict(by_alias=True, exclude_none=True, exclude_unset=True)
            result = await self.client.insert_one(memory_dict)
            return str(result.inserted_id)
        except PyMongoError as exc:
            raise NewApplicationError(CommonDatabaseQueryError, exc)

    async def find_by_user_id(self, user_id: str, limit: int = 50) -> List[EpisodicMemory]:
        try:
            cursor = self.client.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
            documents = await cursor.to_list(length=None)
            return [EpisodicMemory(**_normalize_document_id(doc)) for doc in documents]
        except PyMongoError as exc:
            raise NewApplicationError(CommonDatabaseQueryError, exc)

    async def find_by_ids(self, ids: List[str]) -> List[EpisodicMemory]:
        try:
            id_candidates = []
            for memory_id in ids:
                id_candidates.extend(_build_id_candidates(memory_id))
            cursor = self.client.find({"_id": {"$in": id_candidates}})
            documents = await cursor.to_list(length=None)
            return [EpisodicMemory(**_normalize_document_id(doc)) for doc in documents]
        except PyMongoError as exc:
            raise NewApplicationError(CommonDatabaseQueryError, exc)

    async def update_access(self, memory_id: str) -> None:
        try:
            await self.client.update_one(
                {"_id": {"$in": _build_id_candidates(memory_id)}},
                {
                    "$set": {"last_accessed": datetime.now(timezone.utc)},
                    "$inc": {"access_count": 1},
                },
            )
        except PyMongoError as exc:
            logger.warning("Failed to update access for memory %s: %s", memory_id, exc)

    async def delete_by_id(self, memory_id: str) -> None:
        try:
            await self.client.delete_one({"_id": {"$in": _build_id_candidates(memory_id)}})
        except PyMongoError as exc:
            raise NewApplicationError(CommonDatabaseQueryError, exc)

    async def find_unconsolidated(self, user_id: str, min_importance: int = 7) -> List[EpisodicMemory]:
        try:
            cursor = self.client.find({
                "user_id": user_id,
                "importance": {"$gte": min_importance},
            }).sort("importance", -1)
            documents = await cursor.to_list(length=None)
            return [EpisodicMemory(**_normalize_document_id(doc)) for doc in documents]
        except PyMongoError as exc:
            raise NewApplicationError(CommonDatabaseQueryError, exc)

    async def delete_many_by_ids(self, memory_ids: List[str]) -> int:
        if not memory_ids:
            return 0
        try:
            id_candidates = []
            for memory_id in memory_ids:
                id_candidates.extend(_build_id_candidates(memory_id))
            result = await self.client.delete_many({"_id": {"$in": id_candidates}})
            return result.deleted_count
        except PyMongoError as exc:
            raise NewApplicationError(CommonDatabaseQueryError, exc)

    async def ensure_indexes(self) -> None:
        try:
            await self.client.create_index([("user_id", 1), ("created_at", -1)])
            await self.client.create_index([("user_id", 1), ("importance", -1)])
            logger.info("Episodic memory indexes ensured")
        except Exception as exc:
            logger.warning("Failed to ensure episodic memory indexes: %s", exc)

    async def find_stale(
        self,
        user_id: str,
        max_importance: int,
        older_than_days: int,
        require_zero_access: bool = False,
    ) -> List[EpisodicMemory]:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            query: dict = {
                "user_id": user_id,
                "importance": {"$lte": max_importance},
                "created_at": {"$lt": cutoff},
            }
            if require_zero_access:
                query["access_count"] = 0
            cursor = self.client.find(query)
            documents = await cursor.to_list(length=None)
            return [EpisodicMemory(**_normalize_document_id(doc)) for doc in documents]
        except PyMongoError as exc:
            raise NewApplicationError(CommonDatabaseQueryError, exc)
