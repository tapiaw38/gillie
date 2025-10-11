from fastapi import HTTPException, status
from typing import List, Optional
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

    async def create(self, faq_input: FAQInput):
        try:
            faq = FAQ(
                question=faq_input.question,
                answer=faq_input.answer,
                category=faq_input.category,
                tags=faq_input.tags,
                is_active=faq_input.is_active,
                order=faq_input.order,
            )

            created_faq = self.usecase.create_usecase.execute(faq)

            if created_faq is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="FAQ not created",
                )

            return FAQOutput.from_output(created_faq)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    async def find_by_id(self, faq_id: str):
        try:
            faq = self.usecase.find_by_id_usecase.execute(faq_id)
            if faq is None:
                return None
            return FAQOutput.from_output(faq)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    async def find_all(self, category: Optional[str] = None, is_active: Optional[bool] = None):
        try:
            faqs = self.usecase.find_all_usecase.execute(category, is_active)
            return FAQListOutput.from_output(faqs)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    async def find_by_category(self, category: str):
        try:
            faqs = self.usecase.find_by_category_usecase.execute(category)
            return FAQListOutput.from_output(faqs)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    async def update(self, faq_id: str, faq_update: FAQUpdate):
        try:
            # Obtener el FAQ actual
            existing_faq = self.usecase.find_by_id_usecase.execute(faq_id)
            if existing_faq is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"FAQ with id {faq_id} not found"
                )

            # Crear FAQ con los valores actualizados
            updated_data = existing_faq.dict()
            update_dict = faq_update.dict(exclude_unset=True, exclude_none=True)
            updated_data.update(update_dict)

            updated_faq = FAQ(**updated_data)
            result = self.usecase.update_usecase.execute(faq_id, updated_faq)

            return FAQOutput.from_output(result)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    async def delete(self, faq_id: str):
        try:
            deleted = self.usecase.delete_usecase.execute(faq_id)
            return deleted
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
