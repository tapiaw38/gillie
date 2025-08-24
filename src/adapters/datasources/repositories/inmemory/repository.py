from typing import TypeVar, Generic, List, Optional, Protocol
from abc import ABC, abstractmethod


class CodedEntity(Protocol):
    """Protocol for entities that have a get_code method"""

    def get_code(self) -> str: ...


# Generic type variable constrained to entities with get_code method
T = TypeVar("T", bound=CodedEntity)


class Repository(Generic[T], ABC):
    """Generic repository interface"""

    @abstractmethod
    def list(self) -> List[T]:
        """Return all entities"""
        pass

    @abstractmethod
    def get(self, code: str) -> Optional[T]:
        """Get entity by code"""
        pass


class InMemoryRepository(Repository[T]):
    """In-memory implementation of the generic repository"""

    def __init__(self, data: List[T]):
        self._data = data

    def list(self) -> List[T]:
        """Return all entities"""
        return self._data.copy()

    def get(self, code: str) -> Optional[T]:
        """Get entity by code"""
        for item in self._data:
            if item.get_code() == code:
                return item
        return None


def new_repository(data: List[T]) -> Repository[T]:
    """Factory function to create a new repository instance"""
    return InMemoryRepository(data)
