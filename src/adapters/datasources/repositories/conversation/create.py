from pymongo.errors import PyMongoError
from src.core.domain.model import Conversation


def create_conversation(client, conversation: Conversation) -> str:
    try:
        conversation_dict = conversation.dict(by_alias=True, exclude_none=True, exclude_unset=True)
        result = client.insert_one(conversation_dict)
        conversation_id = str(result.inserted_id)
        return conversation_id
    except PyMongoError as e:
        raise Exception(f"Error creating conversation: {e}")
