from typing import List
from pymongo.errors import PyMongoError
from src.core.domain import Conversation
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import ConversationListQueryError


def find_unextracted_conversations(client, user_id: str) -> List[Conversation]:
    """Return non-sandbox conversations where memory_extracted is False and message_count > 0."""
    try:
        query_filter = {
            "profile.user_id": user_id,
            "is_sandbox": {"$ne": True},
            "$or": [
                {"memory_extracted": {"$exists": False}},
                {"memory_extracted": False},
            ],
            "message_count": {"$gt": 0},
        }
        cursor = client.find(query_filter).sort("created_at", -1)
        documents = list(cursor)
        return [
            Conversation(**{
                **doc,
                "id": str(doc["_id"]),
                "message_count": len(doc.get("messages", [])),
            })
            for doc in documents
        ]
    except PyMongoError as e:
        raise NewApplicationError(ConversationListQueryError, e)
