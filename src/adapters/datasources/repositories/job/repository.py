from typing import List, Optional

from src.adapters.datasources.datasources import Datasources
from src.core.domain.job import Job
from .repository_interface import RepositoryInterface
from .create import create
from .find_by_id import find_by_id
from .find_all import find_all
from .find_all_enabled import find_all_enabled
from .update import update
from .delete import delete


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.client = datasources.no_sql_jobs_client
        self.client.create_index("profile_id")
        self.client.create_index("enabled")

    def create(self, job: Job) -> str:
        return create(self.client, job)

    def find_by_id(self, job_id: str) -> Optional[Job]:
        return find_by_id(self.client, job_id)

    def find_all(self, profile_id: str) -> List[Job]:
        return find_all(self.client, profile_id)

    def find_all_enabled(self) -> List[Job]:
        return find_all_enabled(self.client)

    def update(self, job: Job) -> None:
        update(self.client, job)

    def delete(self, job_id: str) -> None:
        delete(self.client, job_id)
