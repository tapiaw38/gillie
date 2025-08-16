from abc import ABC, abstractmethod
from typing import List, Optional
from src.core.domain.model import (
    Conversation,
    Message,
    Profile,
)


class RepositoryInterface(ABC):
    @abstractmethod
    def create(self, conversation: Conversation) -> str:
        pass

    @abstractmethod
    def find_by_id(self, id: str) -> Conversation:
        pass

    @abstractmethod
    def find_user_id(self, user_id: str) -> List[Conversation]:
        pass

    @abstractmethod
    def update_profile_by_user_id(self, user_id: str, profile: Profile) -> str:
        pass

    @abstractmethod
    def update_messages_by_id(self, id: str, messages: List[Message]) -> None:
        pass
