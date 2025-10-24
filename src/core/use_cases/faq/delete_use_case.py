from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.faq import FAQDeleteNotFoundError
from src.core.platform.errors.mappings.profile import ProfileGetNotFoundError
from src.core.platform.errors.mappings.common import UnauthorizedError
from pymongo.errors import PyMongoError


class DeleteUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, faq_id: str, user_id: str) -> bool:
        try:
            # Get profile from user_id
            profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileGetNotFoundError)

            existing_faq = self.context_factory.repositories.faq.find_by_id(faq_id)
            if not existing_faq:
                raise NewApplicationError(FAQDeleteNotFoundError)

            # Verify FAQ belongs to user
            if existing_faq.profile_id != profile.id:
                raise NewApplicationError(UnauthorizedError)

            deleted = self.context_factory.repositories.faq.delete(faq_id)
            return deleted

        except PyMongoError as e:
            from src.core.platform.errors.mappings.faq import FAQDeleteQueryError
            raise NewApplicationError(FAQDeleteQueryError, e)
