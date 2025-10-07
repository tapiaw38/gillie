from typing import List
from pymongo.errors import PyMongoError
from src.core.domain import Message


def update_messages_by_id(client, id: str, messages: List[Message]) -> None:
    try:
        messages_dict = [message.dict(by_alias=True) for message in messages]
        result = client.update_one(
            {"_id": id},
            {"$set": {"messages": messages_dict}}
        )

        if result.matched_count == 0:
            raise Exception(f"No conversation found with id: {id}")

    except PyMongoError as e:
        raise Exception(f"Error updating conversation: {e}")
