from pymongo.errors import PyMongoError
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import ConversationUpdateQueryError


def update_conversation_summary(client, conversation_id: str, summary: str, memory_extracted: bool) -> None:
    try:
        client.update_one(
            {"_id": conversation_id},
            {"$set": {"summary": summary, "memory_extracted": memory_extracted}},
        )
    except PyMongoError as e:
        raise NewApplicationError(ConversationUpdateQueryError, e)
