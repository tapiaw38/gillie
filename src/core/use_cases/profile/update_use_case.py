from src.schemas import ProfileInput, ProfileOutput
from src.core.domain import Profile
from datetime import datetime, timezone
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import (
    ProfileUpdateQueryError,
    ProfileUpdateNotFoundError,
    ProfileUpdateValidationError
)


class UpdateUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str, profile: ProfileInput):
        # Validation
        if not profile.assistant_name or profile.assistant_name.strip() == "":
            raise NewApplicationError(ProfileUpdateValidationError)

        if not profile.business_name or profile.business_name.strip() == "":
            raise NewApplicationError(ProfileUpdateValidationError)

        try:
            updated_profile = Profile(
                assistant_name=profile.assistant_name,
                business_name=profile.business_name,
                functions=profile.functions,
                business_context=profile.business_context,
                role=profile.role,
                tts_enabled=profile.tts_enabled,
                updated_at=datetime.now(timezone.utc),
            )

            search_profile = self.context_factory.repositories.profile.find_by_user_id(
                user_id
            )
            if not search_profile:
                raise NewApplicationError(ProfileUpdateNotFoundError)

            profile_updated_id = self.context_factory.repositories.profile.update(
                search_profile.id, updated_profile
            )
            if not profile_updated_id:
                raise NewApplicationError(ProfileUpdateNotFoundError)

            profile_updated = self.context_factory.repositories.profile.find_by_id(
                profile_updated_id
            )
            if not profile_updated:
                raise NewApplicationError(ProfileUpdateNotFoundError)

            self.context_factory.repositories.conversation.update_profile_by_user_id(
                user_id,
                profile=profile_updated,
            )

            return ProfileOutput.from_output(profile_updated)

        except PyMongoError as e:
            raise NewApplicationError(ProfileUpdateQueryError, e)