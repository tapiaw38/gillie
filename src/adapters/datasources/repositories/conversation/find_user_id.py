from typing import List
from pymongo.errors import PyMongoError
from src.core.domain import Conversation
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import ConversationListQueryError


def find_conversations_by_user_id(
    client, user_id: str, include_sandbox: bool = False
) -> List[Conversation]:
    """
    Find conversations by user ID.

    Args:
        client: MongoDB client
        user_id: User ID to search for
        include_sandbox: If False (default), excludes sandbox conversations.
                        If True, includes all conversations (sandbox and production).

    Returns:
        List of conversations sorted by creation date (newest first)

    Raises:
        Exception: If database error occurs
    """
    try:
        query_filter = {"profile.user_id": user_id}

        if not include_sandbox:
            query_filter["is_sandbox"] = {"$ne": True}

        cursor = client.find(query_filter).sort("created_at", -1)
        documents = list(cursor)
        return [
            Conversation(**{
                **doc,
                "id": str(doc["_id"]),
                "message_count": len(doc.get("messages", []))
            })
            for doc in documents
        ]
    except PyMongoError as e:
        raise NewApplicationError(ConversationListQueryError, e)


def find_sandbox_conversations_by_user_id(client, user_id: str) -> List[Conversation]:
    """
    Find only sandbox conversations by user ID.

    Args:
        client: MongoDB client
        user_id: User ID to search for

    Returns:
        List of sandbox conversations sorted by creation date (newest first)

    Raises:
        Exception: If database error occurs
    """
    try:
        query_filter = {
            "profile.user_id": user_id,
            "is_sandbox": True
        }

        cursor = client.find(query_filter).sort("created_at", -1)
        documents = list(cursor)
        return [
            Conversation(**{
                **doc,
                "id": str(doc["_id"]),
                "message_count": len(doc.get("messages", []))
            })
            for doc in documents
        ]
    except PyMongoError as e:
        raise NewApplicationError(ConversationListQueryError, e)
