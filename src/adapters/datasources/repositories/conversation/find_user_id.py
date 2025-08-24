from typing import List
from pymongo.errors import PyMongoError
from src.core.domain.model import Conversation


def find_conversations_by_user_id(client, user_id: str) -> List[Conversation]:
    try:
        cursor = client.find({"profile.user_id": user_id}).sort("created_at", -1)
        documents = list(cursor)
        return [
            Conversation(**{**doc, "id": str(doc["_id"])})
            for doc in documents
        ]
    except PyMongoError as e:
        raise Exception(f"Error finding conversations by user_id: {e}")
