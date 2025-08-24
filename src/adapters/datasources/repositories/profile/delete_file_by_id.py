from pymongo.errors import PyMongoError


def delete_file_by_id(client, user_id: str, file_id: str) -> None:
    try:
        result = client.update_one(
            {"user_id": user_id},
            {"$pull": {"files": {"_id": file_id}}}
        )

        if result.matched_count == 0:
            raise Exception(f"No profile found with user_id: {user_id}")

    except PyMongoError as e:
        raise Exception(f"Error deleting file by ID: {e}")
    except Exception as e:
        raise Exception(f"Unexpected error: {e}")
