from pymongo.errors import PyMongoError


def delete_faq(client, id: str) -> bool:
    try:
        result = client.delete_one({"_id": id})
        return result.deleted_count > 0
    except PyMongoError as e:
        raise Exception(f"Error deleting FAQ: {e}")
