from typing import Optional
from src.schemas import (
    FAQInput,
    FAQUpdate,
    FAQOutput,
    FAQListOutput,
)
from src.core.use_cases.use_cases import FAQ as FAQUsecases
from src.core.domain import FAQ


class FAQService:
    def __init__(self, usecase: FAQUsecases):
        self.usecase = usecase

    async def create(self, faq_input: FAQInput, user_id: str):
        faq = FAQ(
            profile_id="",  # Will be set by use case
            question=faq_input.question,
            answer=faq_input.answer,
            category=faq_input.category,
            tags=faq_input.tags,
            is_active=faq_input.is_active,
            order=faq_input.order,
        )

        created_faq = self.usecase.create_usecase.execute(faq, user_id)
        return FAQOutput.from_output(created_faq)

    async def find_by_id(self, faq_id: str):
        faq = self.usecase.find_by_id_usecase.execute(faq_id)
        if faq is None:
            return None
        return FAQOutput.from_output(faq)

    async def find_all(self, user_id: str, category: Optional[str] = None, is_active: Optional[bool] = None):
        faqs = self.usecase.find_all_usecase.execute(user_id, category, is_active)
        return FAQListOutput.from_output(faqs)

    async def find_by_category(self, user_id: str, category: str):
        faqs = self.usecase.find_by_category_usecase.execute(user_id, category)
        return FAQListOutput.from_output(faqs)

    async def update(self, faq_id: str, faq_update: FAQUpdate, user_id: str):
        # Get existing FAQ
        existing_faq = self.usecase.find_by_id_usecase.execute(faq_id)
        from src.core.platform.errors import NewApplicationError
        from src.core.platform.errors.mappings.faq import FAQUpdateNotFoundError

        if existing_faq is None:
            raise NewApplicationError(FAQUpdateNotFoundError)

        updated_data = existing_faq.dict()
        update_dict = faq_update.dict(exclude_unset=True, exclude_none=True)
        updated_data.update(update_dict)

        updated_faq = FAQ(**updated_data)
        result = self.usecase.update_usecase.execute(faq_id, updated_faq, user_id)

        return FAQOutput.from_output(result)

    async def delete(self, faq_id: str, user_id: str):
        deleted = self.usecase.delete_usecase.execute(faq_id, user_id)
        return deleted
