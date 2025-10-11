from abc import ABC, abstractmethod
from typing import List, Optional
from src.core.domain import FAQ


class RepositoryInterface(ABC):
    @abstractmethod
    def create(self, faq: FAQ) -> str:
        pass

    @abstractmethod
    def find_by_id(self, id: str) -> Optional[FAQ]:
        pass

    @abstractmethod
    def find_all(self, category: Optional[str] = None, is_active: Optional[bool] = None) -> List[FAQ]:
        pass

    @abstractmethod
    def update(self, id: str, faq: FAQ) -> str:
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        pass

    @abstractmethod
    def find_by_category(self, category: str) -> List[FAQ]:
        pass
