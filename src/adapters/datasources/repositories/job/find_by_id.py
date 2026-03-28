from typing import Optional

from pymongo.errors import PyMongoError

from src.core.domain.job import Job
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.job import JobGetQueryError


def find_by_id(client, job_id: str) -> Optional[Job]:
    try:
        doc = client.find_one({"_id": job_id})
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        return Job(**doc)
    except PyMongoError as e:
        raise NewApplicationError(JobGetQueryError, e)
