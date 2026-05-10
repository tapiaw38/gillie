from pymongo import MongoClient as PyMongoClient, collection, errors
from pymongo.asynchronous.mongo_client import AsyncMongoClient as PyMongoAsyncClient
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult, UpdateResult as ReplaceResult
from pymongo.cursor import Cursor
from typing import Protocol, Any, Optional, List
from src.core.platform.nosql.migrations import Migration
import logging


class Client(Protocol):
    def disconnect(self) -> None: ...
    def get_collection(self) -> collection.Collection: ...
    def insert_one(self, document: dict) -> InsertOneResult: ...
    def find(self, filter: dict) -> Cursor: ...
    def find_one(self, filter: dict) -> Optional[dict]: ...
    def update_many(self, filter: dict, update: dict) -> UpdateResult: ...
    def update_one(self, filter: dict, update: dict) -> UpdateResult: ...
    def replace_one(self, filter: dict, replacement: dict, upsert: bool = False) -> ReplaceResult: ...
    def delete_one(self, filter: dict) -> DeleteResult: ...
    def run_migrations(self, migration_collection: collection.Collection, migrations: List[Migration]) -> None: ...


class AsyncClient(Protocol):
    async def disconnect(self) -> None: ...
    def get_collection(self) -> Any: ...
    async def insert_one(self, document: dict) -> InsertOneResult: ...
    def find(self, filter: dict) -> Any: ...
    async def find_one(self, filter: dict, projection: Optional[dict] = None) -> Optional[dict]: ...
    async def update_many(self, filter: dict, update: dict) -> UpdateResult: ...
    async def update_one(self, filter: dict, update: dict) -> UpdateResult: ...
    async def replace_one(self, filter: dict, replacement: dict, upsert: bool = False) -> ReplaceResult: ...
    async def delete_one(self, filter: dict) -> DeleteResult: ...
    async def create_index(self, key: str, unique: bool = False) -> None: ...


class MongoDBClient(Client):
    def __init__(self, uri: str, database: str, collection_name: str):
        self.client = PyMongoClient(
            uri,
            connect=False,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
        )
        self.db = self.client[database]
        self._collection = self.db[collection_name]

    def disconnect(self) -> None:
        self.client.close()

    def get_collection(self) -> collection.Collection:
        return self._collection

    def insert_one(self, document: dict) -> InsertOneResult:
        return self._collection.insert_one(document)

    def find(self, filter: dict) -> Cursor:
        return self._collection.find(filter)

    def find_one(self, filter: dict, projection: Optional[dict] = None) -> Optional[dict]:
        return self._collection.find_one(filter, projection)

    def update_many(self, filter: dict, update: dict) -> UpdateResult:
        return self._collection.update_many(filter, update)

    def update_one(self, filter: dict, update: dict) -> UpdateResult:
        return self._collection.update_one(filter, update)

    def replace_one(self, filter: dict, replacement: dict, upsert: bool = False) -> ReplaceResult:
        return self._collection.replace_one(filter, replacement, upsert=upsert)

    def delete_one(self, filter: dict) -> DeleteResult:
        return self._collection.delete_one(filter)

    def create_index(self, key: str, unique: bool = False) -> None:
        self._collection.create_index(key, unique=unique)

    def run_migrations(self, migration_collection: collection.Collection, migrations: List[Migration]) -> None:
        for migration in migrations:
            existing = migration_collection.find_one({
                "version": migration.version,
                "collection": self._collection.name,
            })

            if existing:
                logging.info(f"Migration version {migration.version} already exists, skipping")
                continue

            logging.info(f"Running migration version {migration.version}")
            migration.up(self.db)

            migration_collection.insert_one({
                "version": migration.version,
                "collection": self._collection.name,
            })

        logging.info("All migrations are up to date")


class AsyncMongoDBClient(AsyncClient):
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

    async def create_index(self, key: str, unique: bool = False) -> None:
        await self._collection.create_index(key, unique=unique)
