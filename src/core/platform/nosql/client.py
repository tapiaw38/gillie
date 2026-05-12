from pymongo.asynchronous.mongo_client import AsyncMongoClient as PyMongoAsyncClient
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult, UpdateResult as ReplaceResult
from typing import Protocol, Any, Optional, List
from src.core.platform.nosql.migrations import Migration
import logging


class Client(Protocol):
    async def disconnect(self) -> None: ...
    def get_collection(self) -> Any: ...
    async def insert_one(self, document: dict) -> InsertOneResult: ...
    def find(self, filter: dict) -> Any: ...
    async def find_one(self, filter: dict, projection: Optional[dict] = None) -> Optional[dict]: ...
    async def update_many(self, filter: dict, update: dict) -> UpdateResult: ...
    async def update_one(self, filter: dict, update: dict) -> UpdateResult: ...
    async def replace_one(self, filter: dict, replacement: dict, upsert: bool = False) -> ReplaceResult: ...
    async def delete_one(self, filter: dict) -> DeleteResult: ...
    async def delete_many(self, filter: dict) -> DeleteResult: ...
    async def create_index(self, key: str, unique: bool = False) -> None: ...
    async def run_migrations(self, migration_collection: Any, migrations: List[Migration]) -> None: ...


class MongoDBClient(Client):
    def __init__(self, uri: str, database: str, collection_name: str):
        self.client = PyMongoAsyncClient(
            uri,
            connect=False,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
        )
        self.db = self.client[database]
        self._collection = self.db[collection_name]

    async def disconnect(self) -> None:
        await self.client.close()

    def get_collection(self) -> Any:
        return self._collection

    async def insert_one(self, document: dict) -> InsertOneResult:
        return await self._collection.insert_one(document)

    def find(self, filter: dict) -> Any:
        return self._collection.find(filter)

    async def find_one(self, filter: dict, projection: Optional[dict] = None) -> Optional[dict]:
        return await self._collection.find_one(filter, projection)

    async def update_many(self, filter: dict, update: dict) -> UpdateResult:
        return await self._collection.update_many(filter, update)

    async def update_one(self, filter: dict, update: dict) -> UpdateResult:
        return await self._collection.update_one(filter, update)

    async def replace_one(self, filter: dict, replacement: dict, upsert: bool = False) -> ReplaceResult:
        return await self._collection.replace_one(filter, replacement, upsert=upsert)

    async def delete_one(self, filter: dict) -> DeleteResult:
        return await self._collection.delete_one(filter)

    async def delete_many(self, filter: dict) -> DeleteResult:
        return await self._collection.delete_many(filter)

    async def create_index(self, key: str, unique: bool = False) -> None:
        await self._collection.create_index(key, unique=unique)

    async def run_migrations(self, migration_collection: Any, migrations: List[Migration]) -> None:
        for migration in migrations:
            existing = await migration_collection.find_one({
                "version": migration.version,
                "collection": self._collection.name,
            })
            if existing:
                logging.info(f"Migration version {migration.version} already exists, skipping")
                continue
            logging.info(f"Running migration version {migration.version}")
            await migration.up(self.db)
            await migration_collection.insert_one({
                "version": migration.version,
                "collection": self._collection.name,
            })
        logging.info("All migrations are up to date")
