from pymongo.errors import PyMongoError
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.faq import FAQDeleteQueryError


def delete_faq(client, id: str) -> bool:
    try:
        result = client.delete_one({"_id": id})
        return result.deleted_count > 0
    except PyMongoError as e:
        raise NewApplicationError(FAQDeleteQueryError, e)
