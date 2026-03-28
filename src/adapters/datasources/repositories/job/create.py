from pymongo.errors import PyMongoError

from src.core.domain.job import Job
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.job import JobCreateError


def create(client, job: Job) -> str:
    try:
        doc = job.dict()
        doc["_id"] = job.id
        client.insert_one(doc)
        return job.id
    except PyMongoError as e:
        raise NewApplicationError(JobCreateError, e)
