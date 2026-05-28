from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.domain.brain import EpisodicMemory


class RepositoryInterface(ABC):
    @abstractmethod
    async def create(self, memory: EpisodicMemory) -> str:
        pass

    @abstractmethod
    async def find_by_user_id(self, user_id: str, limit: int = 50) -> List[EpisodicMemory]:
        pass

    @abstractmethod
    async def find_by_owner_user_id(
        self,
        owner_user_id: str,
        contact_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        pass

    @abstractmethod
    async def find_by_ids(self, ids: List[str]) -> List[EpisodicMemory]:
        pass

    @abstractmethod
    async def update_access(self, memory_id: str) -> None:
        pass

    @abstractmethod
    async def delete_by_id(self, memory_id: str) -> None:
        pass

    @abstractmethod
    async def find_unconsolidated(self, user_id: str, min_importance: int = 7) -> List[EpisodicMemory]:
        pass

    @abstractmethod
    async def delete_many_by_ids(self, memory_ids: List[str]) -> int:
        pass

    @abstractmethod
    async def ensure_indexes(self) -> None:
        pass

    @abstractmethod
    async def find_stale(
        self,
        user_id: str,
        max_importance: int,
        older_than_days: int,
        require_zero_access: bool = False,
    ) -> List[EpisodicMemory]:
        pass
