from src.core.domain import FAQ
from datetime import datetime
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.faq import (
    FAQCreateNotFoundAfterCreationError,
    FAQCreateQuestionRequiredError,
    FAQCreateAnswerRequiredError,
)
from src.core.platform.errors.mappings.profile import ProfileGetNotFoundError
from pymongo.errors import PyMongoError
from uuid import uuid4


class CreateUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, faq: FAQ, user_id: str) -> FAQ:
        # Validations
        if not faq.question or faq.question.strip() == "":
            raise NewApplicationError(FAQCreateQuestionRequiredError)

        if not faq.answer or faq.answer.strip() == "":
            raise NewApplicationError(FAQCreateAnswerRequiredError)

        try:
            # Get profile from user_id
            profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise NewApplicationError(ProfileGetNotFoundError)

            # Get max order for this user's FAQs
            all_faqs = self.context_factory.repositories.faq.find_all(profile.id)
            max_order = max([f.order for f in all_faqs], default=-1)
            next_order = max_order + 1

            generated_id = str(uuid4())
            new_faq = FAQ(
                _id=generated_id,
                profile_id=profile.id,
                question=faq.question,
                answer=faq.answer,
                category=faq.category,
                tags=faq.tags,
                is_active=faq.is_active if faq.is_active is not None else True,
                order=next_order,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            faq_id = self.context_factory.repositories.faq.create(new_faq)
            created_faq = self.context_factory.repositories.faq.find_by_id(faq_id)

            if not created_faq:
                raise NewApplicationError(FAQCreateNotFoundAfterCreationError)

            return created_faq

        except PyMongoError as e:
            from src.core.platform.errors.mappings.faq import FAQCreateQueryError
            raise NewApplicationError(FAQCreateQueryError, e)
