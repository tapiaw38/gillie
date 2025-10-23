from pymongo.errors import PyMongoError
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import (
    ConversationDeleteQueryError,
    ConversationDeleteNotFoundError
)


def delete_conversation_by_id(client, conversation_id: str) -> None:
    try:
        result = client.delete_one({"_id": conversation_id})

        if result.deleted_count == 0:
            raise NewApplicationError(ConversationDeleteNotFoundError)

    except PyMongoError as e:
        raise NewApplicationError(ConversationDeleteQueryError, e)
