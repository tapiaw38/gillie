from typing import Optional
from pymongo.errors import PyMongoError
from src.core.domain.model import Conversation


def find_conversation_by_id(client, id: str) -> Optional[Conversation]:
    try:
        document = client.find_one({"_id": id})
        if document:
            return Conversation(**document)
        return None
    except PyMongoError as e:
        raise Exception(f"Error finding conversation by ID: {e}")
