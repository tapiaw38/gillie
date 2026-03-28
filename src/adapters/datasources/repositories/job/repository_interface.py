from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.domain.job import Job


class RepositoryInterface(ABC):
    @abstractmethod
    def create(self, job: Job) -> str: ...

    @abstractmethod
    def find_by_id(self, job_id: str) -> Optional[Job]: ...

    @abstractmethod
    def find_all(self, profile_id: str) -> List[Job]: ...

    @abstractmethod
    def find_all_enabled(self) -> List[Job]: ...

    @abstractmethod
    def update(self, job: Job) -> None: ...

    @abstractmethod
    def delete(self, job_id: str) -> None: ...
