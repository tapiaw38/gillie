from pymongo.errors import PyMongoError
from src.core.domain import FAQ
from typing import List, Optional
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.faq import FAQListQueryError


def find_all_faqs(client, category: Optional[str] = None, is_active: Optional[bool] = None) -> List[FAQ]:
    try:
        query = {}
        if category:
            query["category"] = category
        if is_active is not None:
            query["is_active"] = is_active

        faqs = client.find(query).sort("order", 1)
        faq_list = []
        for faq in faqs:
            faq["_id"] = str(faq["_id"])
            faq_list.append(FAQ(**faq))
        return faq_list
    except PyMongoError as e:
        raise NewApplicationError(FAQListQueryError, e)
