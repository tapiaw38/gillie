from src.schemas import ProfileInput, ProfileOutput
from src.core.domain import Profile
from datetime import datetime, timezone
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileCreateQueryError,
    ProfileCreateNameRequiredError,
    ProfileCreateNotFoundAfterCreationError
)
from uuid import uuid4


class CreateUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, profile: ProfileInput, user_id: str):
        if not profile.assistant_name or profile.assistant_name.strip() == "":
            raise NewApplicationError(ProfileCreateNameRequiredError)

        try:
            context = self.context_factory()
            generated_id = str(uuid4())
            new_profile = Profile(
                _id=generated_id,
                user_id=user_id,
                assistant_name=profile.assistant_name,
                business_name=profile.business_name,
                functions=profile.functions,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )

            profile_id = await context.repositories.profile.create(new_profile)
            created_profile = await context.repositories.profile.find_by_id(
                profile_id
            )

            if not created_profile:
                raise NewApplicationError(ProfileCreateNotFoundAfterCreationError)

            return ProfileOutput.from_output(created_profile)

        except PyMongoError as e:
            raise NewApplicationError(ProfileCreateQueryError, e)
