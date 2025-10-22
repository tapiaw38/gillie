from src.schemas import ProfileInput, ProfileOutput
from src.core.domain import Profile
from datetime import datetime, timezone
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileCreateQueryError,
    ProfileCreateNameRequiredError,
    ProfileCreateBusinessNameRequiredError,
    ProfileCreateNotFoundAfterCreationError
)
from uuid import uuid4


class CreateUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, profile: ProfileInput, user_id: str):
        # Validation
        if not profile.assistant_name or profile.assistant_name.strip() == "":
            raise NewApplicationError(ProfileCreateNameRequiredError)

        if not profile.business_name or profile.business_name.strip() == "":
            raise NewApplicationError(ProfileCreateBusinessNameRequiredError)

        try:
            generated_id = str(uuid4())
            iteration_limit = 100
            new_profile = Profile(
                _id=generated_id,
                user_id=user_id,
                assistant_name=profile.assistant_name,
                business_name=profile.business_name,
                functions=profile.functions,
                business_context=profile.business_context,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                iteration_limit=iteration_limit,
            )

            profile_id = self.context_factory.repositories.profile.create(new_profile)
            created_profile = self.context_factory.repositories.profile.find_by_id(
                profile_id
            )

            if not created_profile:
                raise NewApplicationError(ProfileCreateNotFoundAfterCreationError)

            return ProfileOutput.from_output(created_profile)

        except PyMongoError as e:
            raise NewApplicationError(ProfileCreateQueryError, e)