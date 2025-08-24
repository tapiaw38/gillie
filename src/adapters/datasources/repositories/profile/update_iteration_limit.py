from pymongo.errors import PyMongoError


def update_iteration_limit(client, user_id: str, iteration_limit: int) -> str:
    try:
        result = client.update_one(
            {"user_id": user_id},
            {"$set": {"iteration_limit": iteration_limit}}
        )

        if result.matched_count == 0:
            raise Exception(f"No profile found with user_id: {user_id}")

        return user_id

    except PyMongoError as e:
        raise Exception(f"Error updating profile: {e}")
