from pymongo.errors import PyMongoError
from src.core.domain import FAQ
from datetime import datetime


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
            raise Exception(f"FAQ with id {id} not found")

        return id
    except PyMongoError as e:
        raise Exception(f"Error updating FAQ: {e}")
