from pymongo.errors import PyMongoError
from src.core.domain import FAQ
from typing import Optional
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.faq import FAQGetQueryError


def find_faq_by_id(client, id: str) -> Optional[FAQ]:
    try:
        faq = client.find_one({"_id": id})
        if faq:
            return FAQ(**faq)
        return None
    except PyMongoError as e:
        raise NewApplicationError(FAQGetQueryError, e)
