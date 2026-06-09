from abc import ABC, abstractmethod
from typing import List, Optional
from src.core.domain import (
    Profile,
    ApiKey,
    Contact,
    File,
    Integration,
)


class RepositoryInterface(ABC):
    @abstractmethod
    async def create(self, profile: Profile) -> str:
        pass

    @abstractmethod
    async def find_by_id(self, id: str) -> Profile:
        pass

    @abstractmethod
    async def find_by_user_id(self, user_id: str) -> Profile:
        pass

    @abstractmethod
    async def find_all_user_ids(self) -> List[str]:
        pass

    @abstractmethod
    async def find_all(self) -> List[Profile]:
        pass

    @abstractmethod
    async def update(self, user_id: str, profile: Profile) -> str:
        pass

    @abstractmethod
    async def update_api_keys(self, user_id: str, api_keys: List[ApiKey]) -> Optional[List[ApiKey]]:
        pass

    @abstractmethod
    async def deactivate_api_key(self, user_id: str, api_key_id: str) -> Optional[str]:
        pass

    @abstractmethod
    async def find_by_api_key_value(self, user_id: str, api_key_value: str) -> ApiKey:
        pass

    @abstractmethod
    async def update_iteration_limit(self, user_id: str, iteration_limit: int) -> str:
        pass

    @abstractmethod
    async def update_files(self, user_id: str, files: List[File]) -> None:
        pass

    @abstractmethod
    async def update_contacts(self, user_id: str, contacts: List[Contact]) -> None:
        pass

    @abstractmethod
    async def delete_file_by_id(self, user_id: str, file_id: str) -> None:
        pass

    @abstractmethod
    async def get_file_by_id(self, user_id: str, file_id: str) -> Optional[File]:
        pass

    @abstractmethod
    async def update_integrations(self, user_id: str, integrations: List[Integration]) -> None:
        pass
