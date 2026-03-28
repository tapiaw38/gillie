from typing import List

from pymongo.errors import PyMongoError

from src.core.domain.job import Job
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.job import JobListQueryError


def find_all_enabled(client) -> List[Job]:
    try:
        cursor = client.find({"enabled": True})
        jobs = []
        for doc in cursor:
            doc["id"] = doc.pop("_id")
            jobs.append(Job(**doc))
        return jobs
    except PyMongoError as e:
        raise NewApplicationError(JobListQueryError, e)
