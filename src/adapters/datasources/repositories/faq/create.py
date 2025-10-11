from pymongo.errors import PyMongoError
from src.core.domain import FAQ


def create_faq(client, faq: FAQ) -> str:
    try:
        faq_dict = faq.dict(by_alias=True, exclude_none=True)
        result = client.insert_one(faq_dict)
        faq_id = str(result.inserted_id)
        return faq_id
    except PyMongoError as e:
        raise Exception(f"Error creating FAQ: {e}")
