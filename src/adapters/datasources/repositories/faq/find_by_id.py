from pymongo.errors import PyMongoError
from src.core.domain import FAQ
from typing import Optional


def find_faq_by_id(client, id: str) -> Optional[FAQ]:
    try:
        faq = client.find_one({"_id": id})
        if faq:
            return FAQ(**faq)
        return None
    except PyMongoError as e:
        raise Exception(f"Error finding FAQ by id: {e}")
