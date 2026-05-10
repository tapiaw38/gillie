from typing import List, Optional

from src.adapters.datasources.datasources import Datasources
from src.core.domain.job import Job
from pymongo.errors import PyMongoError

from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.job import (
    JobCreateError,
    JobDeleteError,
    JobGetQueryError,
    JobListQueryError,
    JobUpdateError,
)
from .repository_interface import RepositoryInterface


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.client = datasources.no_sql_jobs_client
 
    async def ensure_indexes(self) -> None:
        await self.client.create_index("profile_id")
        await self.client.create_index("enabled")

    async def create(self, job: Job) -> str:
        try:
            doc = job.dict()
            doc["_id"] = job.id
            await self.client.insert_one(doc)
            return job.id
        except PyMongoError as exc:
            raise NewApplicationError(JobCreateError, exc)

    async def find_by_id(self, job_id: str) -> Optional[Job]:
        try:
            doc = await self.client.find_one({"_id": job_id})
            if not doc:
                return None
            doc["id"] = doc.pop("_id")
            return Job(**doc)
        except PyMongoError as exc:
            raise NewApplicationError(JobGetQueryError, exc)

    async def find_all(self, profile_id: str) -> List[Job]:
        try:
            cursor = self.client.find({"profile_id": profile_id})
            jobs = []
            for doc in await cursor.to_list(length=None):
                doc["id"] = doc.pop("_id")
                jobs.append(Job(**doc))
            return jobs
        except PyMongoError as exc:
            raise NewApplicationError(JobListQueryError, exc)

    async def find_all_enabled(self) -> List[Job]:
        try:
            cursor = self.client.find({"enabled": True})
            jobs = []
            for doc in await cursor.to_list(length=None):
                doc["id"] = doc.pop("_id")
                jobs.append(Job(**doc))
            return jobs
        except PyMongoError as exc:
            raise NewApplicationError(JobListQueryError, exc)

    async def update(self, job: Job) -> None:
        try:
            doc = job.dict()
            doc.pop("id", None)
            await self.client.update_one({"_id": job.id}, {"$set": doc})
        except PyMongoError as exc:
            raise NewApplicationError(JobUpdateError, exc)

    async def delete(self, job_id: str) -> None:
        try:
            await self.client.delete_one({"_id": job_id})
        except PyMongoError as exc:
            raise NewApplicationError(JobDeleteError, exc)
