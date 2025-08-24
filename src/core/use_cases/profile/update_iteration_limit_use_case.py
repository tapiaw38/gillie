from src.schemas.schemas import ProfileOutput
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory


class UpdateIterationLimitUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    async def execute(self, user_id: str, iteration_limit: int):
        try:
            profile_user_id = (
                self.context_factory.repositories.profile.update_iteration_limit(
                    user_id, iteration_limit
                )
            )
            if not profile_user_id:
                raise Exception(f"No profile found with id: {profile_user_id}")

            profile_updated = self.context_factory.repositories.profile.find_by_user_id(
                profile_user_id
            )
            if not profile_updated:
                raise Exception(
                    f"No profile found with user_id: {user_id} after update"
                )

            self.context_factory.repositories.conversation.update_profile_by_user_id(
                user_id,
                profile=profile_updated,
            )

            return ProfileOutput.from_output(profile_updated)

        except PyMongoError as e:
            raise Exception(f"Error interacting with database: {e}")

        except Exception as e:
            raise Exception(f"Error executing UpdateIterationLimitUseCase: {e}")