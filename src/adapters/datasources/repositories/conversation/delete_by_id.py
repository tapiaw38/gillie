from pymongo.errors import PyMongoError


def delete_conversation_by_id(client, conversation_id: str) -> None:
    try:
        result = client.delete_one({"_id": conversation_id})

        if result.deleted_count == 0:
            raise Exception(f"Conversation with id {conversation_id} not found")

    except PyMongoError as e:
        raise Exception(f"Error deleting conversation by id: {e}")
