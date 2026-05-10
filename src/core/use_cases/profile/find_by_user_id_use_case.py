from src.schemas import ProfileOutput
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileGetQueryError,
    ProfileGetNotFoundError
)


class FindByUserIdUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str):
        try:
            context = self.context_factory()
            profile = await context.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileGetNotFoundError)
            return ProfileOutput.from_output(profile)

        except PyMongoError as e:
            raise NewApplicationError(ProfileGetQueryError, e)
