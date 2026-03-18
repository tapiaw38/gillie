from typing import List

from pymongo.errors import PyMongoError

from src.core.domain.job import Job
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.job import JobListQueryError


def find_all(client, profile_id: str) -> List[Job]:
    try:
        cursor = client.find({"profile_id": profile_id})
        jobs = []
        for doc in cursor:
            doc["id"] = doc.pop("_id")
            jobs.append(Job(**doc))
        return jobs
    except PyMongoError as e:
        raise NewApplicationError(JobListQueryError, e)
