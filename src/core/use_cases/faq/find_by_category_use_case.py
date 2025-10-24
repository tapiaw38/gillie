from src.core.domain import FAQ
from typing import List
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import ProfileGetNotFoundError
from pymongo.errors import PyMongoError


class FindByCategoryUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str, category: str) -> List[FAQ]:
        try:
            # Get profile from user_id
            profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileGetNotFoundError)

            faqs = self.context_factory.repositories.faq.find_by_category(profile.id, category)
            return faqs

        except PyMongoError as e:
            from src.core.platform.errors.mappings.faq import FAQListByCategoryQueryError
            raise NewApplicationError(FAQListByCategoryQueryError, e)
