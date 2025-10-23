from pymongo.errors import PyMongoError
from src.core.domain import Profile
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import ConversationUpdateQueryError


def update_profile_by_user_id(client, user_id: str, profile: Profile) -> str:
    try:
        profile_data = profile.dict(by_alias=True, exclude_none=True, exclude_unset=True)

        result = client.update_many(
            {"profile.user_id": user_id},
            {"$set": {"profile": profile_data}}
        )

        if result.matched_count == 0:
            print(f"No conversations found for user_id: {user_id}")

        return user_id

    except PyMongoError as e:
        raise NewApplicationError(ConversationUpdateQueryError, e)
