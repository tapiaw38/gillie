from typing import List
from pymongo.errors import PyMongoError
from src.core.domain import Message
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import (
    ConversationUpdateQueryError,
    ConversationUpdateNotFoundError
)


def update_messages_by_id(client, id: str, messages: List[Message]) -> None:
    try:
        messages_dict = [message.dict(by_alias=True) for message in messages]
        result = client.update_one(
            {"_id": id},
            {"$set": {"messages": messages_dict}}
        )

        if result.matched_count == 0:
            raise NewApplicationError(ConversationUpdateNotFoundError)

    except PyMongoError as e:
        raise NewApplicationError(ConversationUpdateQueryError, e)
