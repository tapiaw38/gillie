from pymongo.errors import PyMongoError

from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.job import JobDeleteError


def delete(client, job_id: str) -> None:
    try:
        client.delete_one({"_id": job_id})
    except PyMongoError as e:
        raise NewApplicationError(JobDeleteError, e)
