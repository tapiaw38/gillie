from src.adapters.datasources.datasources import Datasources
from .repository_interface import RepositoryInterface
from src.core.domain import (
    Profile,
    ApiKey,
    File,
    Integration,
)
from typing import List, Optional
from pymongo.errors import PyMongoError, DuplicateKeyError
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileCreateDuplicateError,
    ProfileCreateQueryError,
    ProfileGetQueryError,
    ProfileUpdateNotFoundError,
    ProfileUpdateQueryError,
)


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.client = datasources.no_sql_profiles_client

    async def ensure_indexes(self) -> None:
        await self.client.create_index("user_id", unique=True)

    async def create(self, profile: Profile) -> str:
        try:
            profile_dict = profile.dict(by_alias=True, exclude_none=True)
            result = await self.client.insert_one(profile_dict)
            return str(result.inserted_id)
        except DuplicateKeyError as exc:
            raise NewApplicationError(ProfileCreateDuplicateError, exc)
        except PyMongoError as exc:
            raise NewApplicationError(ProfileCreateQueryError, exc)

    async def find_by_id(self, id: str) -> Optional[Profile]:
        try:
            document = await self.client.find_one({"_id": id})
            if not document:
                return None
            return Profile(**document)
        except PyMongoError as exc:
            raise NewApplicationError(ProfileGetQueryError, exc)

    async def find_by_user_id(self, user_id: str) -> Profile:
        try:
            document = await self.client.find_one({"user_id": user_id})
            if not document:
                return None
            if "role" not in document or not document["role"]:
                document["role"] = "seller"
            return Profile(**document)
        except PyMongoError as exc:
            raise NewApplicationError(ProfileGetQueryError, exc)

    async def find_all_user_ids(self) -> List[str]:
        try:
            documents = await self.client.find({}).to_list(length=None)
            return [doc["user_id"] for doc in documents if doc.get("user_id")]
        except PyMongoError as exc:
            raise NewApplicationError(ProfileGetQueryError, exc)

    async def find_all(self) -> List[Profile]:
        try:
            documents = await self.client.find({}).to_list(length=None)
            return [Profile(**doc) for doc in documents]
        except PyMongoError as exc:
            raise NewApplicationError(ProfileGetQueryError, exc)

    async def update(self, id: str, profile: Profile) -> str:
        try:
            profile_dict = profile.dict(by_alias=True, exclude_none=True)
            result = await self.client.update_one({"_id": id}, {"$set": profile_dict})
            if result.matched_count == 0:
                raise NewApplicationError(ProfileUpdateNotFoundError)
            return id
        except PyMongoError as exc:
            raise NewApplicationError(ProfileUpdateQueryError, exc)

    async def update_api_keys(self, user_id: str, api_keys: List[ApiKey]) -> None:
        api_keys_dict = [api_key.dict(by_alias=True, exclude_none=True) for api_key in api_keys]
        await self.client.update_one({"user_id": user_id}, {"$set": {"api_keys": api_keys_dict}})

    async def deactivate_api_key(self, user_id: str, api_key_id: str) -> Optional[str]:
        profile = await self.find_by_user_id(user_id)
        if not profile or not profile.api_keys:
            return None
        updated = []
        found = False
        for api_key in profile.api_keys:
            if api_key.id == api_key_id:
                api_key.is_active = False
                found = True
            updated.append(api_key)
        if found:
            await self.update_api_keys(user_id, updated)
            return api_key_id
        return None

    async def find_by_api_key_value(self, user_id: str, api_key_value: str) -> ApiKey:
        profile = await self.find_by_user_id(user_id)
        if not profile or not profile.api_keys:
            return None
        for api_key in profile.api_keys:
            if api_key.value == api_key_value and api_key.is_active:
                return api_key
        return None

    async def update_iteration_limit(self, user_id: str, iteration_limit: int) -> str:
        await self.client.update_one({"user_id": user_id}, {"$set": {"iteration_limit": iteration_limit}})
        return user_id

    async def update_files(self, user_id: str, files: List[File]) -> None:
        files_dict = [file.dict(by_alias=True, exclude_none=True) for file in files]
        await self.client.update_one({"user_id": user_id}, {"$set": {"files": files_dict}})

    async def delete_file_by_id(self, user_id: str, file_id: str) -> None:
        profile = await self.find_by_user_id(user_id)
        if not profile:
            return
        remaining = [file for file in (profile.files or []) if file.id != file_id]
        await self.update_files(user_id, remaining)

    async def get_file_by_id(self, user_id: str, file_id: str) -> Optional[File]:
        profile = await self.find_by_user_id(user_id)
        if not profile or not profile.files:
            return None
        for file in profile.files:
            if file.id == file_id:
                return file
        return None

    async def update_integrations(self, user_id: str, integrations: List[Integration]) -> None:
        integrations_dict = [integration.dict(by_alias=True, exclude_none=True) for integration in integrations]
        await self.client.update_one({"user_id": user_id}, {"$set": {"integrations": integrations_dict}})
