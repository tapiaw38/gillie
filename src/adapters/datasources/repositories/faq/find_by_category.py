from pymongo.errors import PyMongoError
from src.core.domain import FAQ
from typing import List
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.faq import FAQListQueryError


def find_faqs_by_category(client, profile_id: str, category: str) -> List[FAQ]:
    try:
        faqs = client.find({"profile_id": profile_id, "category": category, "is_active": True}).sort("order", 1)
        faq_list = []
        for faq in faqs:
            faq["_id"] = str(faq["_id"])
            faq_list.append(FAQ(**faq))
        return faq_list
    except PyMongoError as e:
        raise NewApplicationError(FAQListQueryError, e)
