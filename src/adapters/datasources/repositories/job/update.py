from pymongo.errors import PyMongoError

from src.core.domain.job import Job
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.job import JobUpdateError


def update(client, job: Job) -> None:
    try:
        doc = job.dict()
        doc.pop("id", None)
        client.update_one({"_id": job.id}, {"$set": doc})
    except PyMongoError as e:
        raise NewApplicationError(JobUpdateError, e)
