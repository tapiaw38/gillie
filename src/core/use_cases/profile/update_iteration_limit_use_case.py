from src.schemas import ProfileOutput
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import ProfileGetNotFoundError


class UpdateIterationLimitUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    async def execute(self, user_id: str, iteration_limit: int):
        profile_user_id = (
            self.context_factory.repositories.profile.update_iteration_limit(
                user_id, iteration_limit
            )
        )
        if not profile_user_id:
            raise NewApplicationError(ProfileGetNotFoundError)

        profile_updated = self.context_factory.repositories.profile.find_by_user_id(
            profile_user_id
        )
        if not profile_updated:
            raise NewApplicationError(ProfileGetNotFoundError)

        self.context_factory.repositories.conversation.update_profile_by_user_id(
            user_id,
            profile=profile_updated,
        )

        return ProfileOutput.from_output(profile_updated)