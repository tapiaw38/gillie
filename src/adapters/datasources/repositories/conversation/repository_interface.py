from abc import ABC, abstractmethod
from typing import List, Optional
from src.core.domain import (
    Conversation,
    Message,
    Profile,
)


class RepositoryInterface(ABC):
    @abstractmethod
    async def create(self, conversation: Conversation) -> str:
        pass

    @abstractmethod
    async def find_by_id(self, id: str) -> Conversation:
        pass

    @abstractmethod
    async def find_user_id(self, user_id: str, include_sandbox: bool = False) -> List[Conversation]:
        pass

    @abstractmethod
    async def find_sandbox_by_user_id(self, user_id: str) -> List[Conversation]:
        pass

    @abstractmethod
    async def update_profile_by_user_id(self, user_id: str, profile: Profile) -> str:
        pass

    @abstractmethod
    async def update_messages_by_id(self, id: str, messages: List[Message]) -> None:
        pass

    @abstractmethod
    async def delete_by_id(self, id: str) -> None:
        pass

    @abstractmethod
    async def update_summary(self, conversation_id: str, summary: str, memory_extracted: bool = True) -> None:
        pass

    @abstractmethod
    async def find_unextracted(self, user_id: str) -> List[Conversation]:
        pass
