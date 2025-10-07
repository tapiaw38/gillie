from abc import ABC, abstractmethod
from typing import List, Optional
from src.core.domain import (
    Profile,
    ApiKey,
    File,
    Integration,
)


class RepositoryInterface(ABC):
    @abstractmethod
    def create(self, profile: Profile) -> str:
        pass

    @abstractmethod
    def find_by_id(self, id: str) -> Profile:
        pass

    @abstractmethod
    def find_by_user_id(self, user_id: str) -> Profile:
        pass

    @abstractmethod
    def find_all_user_ids(self) -> List[str]:
        pass
        
    @abstractmethod
    def find_all(self) -> List[Profile]:
        pass

    @abstractmethod
    def update(self, user_id: str, profile: Profile) -> str:
        pass

    @abstractmethod
    def update_api_keys(self, user_id: str, api_keys: List[ApiKey]) -> Optional[List[ApiKey]]:
        pass

    @abstractmethod
    def deactivate_api_key(self, user_id: str, api_key_id: str) -> Optional[str]:
        pass

    @abstractmethod
    def find_by_api_key_value(self, user_id: str, api_key_value: str) -> ApiKey:
        pass

    @abstractmethod
    def update_iteration_limit(self, user_id: str, iteration_limit: int) -> str:
        pass

    @abstractmethod
    def update_files(self, user_id: str, files: List[File]) -> None:
        pass

    @abstractmethod
    def delete_file_by_id(self, user_id: str, file_id: str) -> None:
        pass

    @abstractmethod
    def get_file_by_id(self, user_id: str, file_id: str) -> Optional[File]:
        pass

    @abstractmethod
    def update_integrations(self, user_id: str, integrations: List[Integration]) -> None:
        pass
