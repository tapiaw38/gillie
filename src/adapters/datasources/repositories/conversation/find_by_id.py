from typing import Optional
from pymongo.errors import PyMongoError
from src.core.domain import Conversation
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import ConversationGetQueryError


def find_conversation_by_id(client, id: str) -> Optional[Conversation]:
    try:
        document = client.find_one({"_id": id})
        if document:
            return Conversation(**document)
        return None
    except PyMongoError as e:
        raise NewApplicationError(ConversationGetQueryError, e)
