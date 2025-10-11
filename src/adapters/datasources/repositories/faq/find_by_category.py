from pymongo.errors import PyMongoError
from src.core.domain import FAQ
from typing import List


def find_faqs_by_category(client, category: str) -> List[FAQ]:
    try:
        faqs = client.find({"category": category, "is_active": True}).sort("order", 1)
        faq_list = []
        for faq in faqs:
            faq["_id"] = str(faq["_id"])
            faq_list.append(FAQ(**faq))
        return faq_list
    except PyMongoError as e:
        raise Exception(f"Error finding FAQs by category: {e}")
