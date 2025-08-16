from typing import List
from pymongo.errors import PyMongoError


def find_all_user_ids(client) -> List[str]:
    try:
        documents = client.find({}, {"_id": 0, "user_id": 1})
        return [doc.get("user_id") for doc in documents if doc.get("user_id")]
    except PyMongoError as e:
        raise RuntimeError(f"Error retrieving user_ids from DB: {e}")
