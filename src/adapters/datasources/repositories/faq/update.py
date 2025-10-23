from pymongo.errors import PyMongoError
from src.core.domain import FAQ
from datetime import datetime
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.faq import (
    FAQUpdateQueryError,
    FAQUpdateNotFoundError
)


def update_faq(client, id: str, faq: FAQ) -> str:
    try:
        faq_dict = faq.dict(by_alias=True, exclude_none=True, exclude_unset=True)
        faq_dict["updated_at"] = datetime.now()
        faq_dict.pop("_id", None)

        result = client.update_one(
            {"_id": id},
            {"$set": faq_dict}
        )

        if result.matched_count == 0:
            raise NewApplicationError(FAQUpdateNotFoundError)

        return id
    except PyMongoError as e:
        raise NewApplicationError(FAQUpdateQueryError, e)
