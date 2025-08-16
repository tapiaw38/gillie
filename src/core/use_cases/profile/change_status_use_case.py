from src.schemas.schemas import ProfileOutput
from src.core.domain.model import Profile
from datetime import datetime, timezone
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory


class ChangeStatusUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str, status: bool):
        try:
            updated_profile = Profile(
                updated_at=datetime.now(timezone.utc),
                is_active=status,
            )

            search_profile = self.context_factory.repositories.profile.find_by_user_id(
                user_id
            )
            if not search_profile:
                raise Exception(f"No profile found with user_id: {user_id}")

            profile_updated_id = self.context_factory.repositories.profile.update(
                search_profile.id, updated_profile
            )
            if not profile_updated_id:
                raise Exception(f"No profile found with id: {search_profile.id}")

            profile_updated = self.context_factory.repositories.profile.find_by_id(
                profile_updated_id
            )
            if not profile_updated:
                raise Exception(
                    f"No profile found with user_id: {user_id} after update"
                )

            return ProfileOutput.from_output(profile_updated)

        except PyMongoError as e:
            raise Exception(f"Error interacting with database: {e}")

        except Exception as e:
            raise Exception(f"Error executing ChangeStatusUseCase: {e}")