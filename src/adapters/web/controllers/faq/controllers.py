from fastapi import APIRouter, status, Depends, Request, Query
from src.schemas import (
    FAQInput,
    FAQUpdate,
    FAQOutput,
    FAQListOutput,
)
from src.core.use_cases.use_cases import Usecases
from src.core.domain import FAQ
from typing import Optional


router = APIRouter(
    prefix="/faq",
    tags=["FAQ"],
)

_usecases_instance = None

def set_usecases(usecases: Usecases):
    """Set the usecases instance (called during app initialization)"""
    global _usecases_instance
    _usecases_instance = usecases

def get_usecases() -> Usecases:
    """Get the usecases instance for dependency injection"""
    if _usecases_instance is None:
        raise Exception("Usecases not initialized. Call set_usecases first.")
    return _usecases_instance


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_faq(
    faq_input: FAQInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    """Create a new FAQ"""
    user_id = request.state.user.get("user_id")

    # Convert input to domain model
    faq = FAQ(
        profile_id="",  # Will be set by use case
        question=faq_input.question,
        answer=faq_input.answer,
        category=faq_input.category,
        tags=faq_input.tags,
        is_active=faq_input.is_active,
        order=faq_input.order,
    )

    created_faq = usecases.faq.create_usecase.execute(faq, user_id)
    return FAQOutput.from_output(created_faq)


@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_faqs(
    request: Request,
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    usecases: Usecases = Depends(get_usecases)
):
    """Get all FAQs for the authenticated user, optionally filtered by category and/or active status"""
    user_id = request.state.user.get("user_id")
    faqs = usecases.faq.find_all_usecase.execute(user_id, category, is_active)
    return FAQListOutput.from_output(faqs)


@router.get("/{faq_id}", status_code=status.HTTP_200_OK)
async def get_faq_by_id(
    faq_id: str,
    usecases: Usecases = Depends(get_usecases)
):
    """Get a specific FAQ by ID"""
    faq = usecases.faq.find_by_id_usecase.execute(faq_id)
    if faq is None:
        from src.core.platform.errors import NewApplicationError
        from src.core.platform.errors.mappings.faq import FAQGetNotFoundError
        raise NewApplicationError(FAQGetNotFoundError)
    return FAQOutput.from_output(faq)


@router.get("/category/{category}", status_code=status.HTTP_200_OK)
async def get_faqs_by_category(
    category: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    """Get all active FAQs for the authenticated user in a specific category"""
    user_id = request.state.user.get("user_id")
    faqs = usecases.faq.find_by_category_usecase.execute(user_id, category)
    return FAQListOutput.from_output(faqs)


@router.put("/{faq_id}", status_code=status.HTTP_200_OK)
async def update_faq(
    faq_id: str,
    faq_update: FAQUpdate,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    """Update an existing FAQ (only if it belongs to the authenticated user)"""
    user_id = request.state.user.get("user_id")

    # Get existing FAQ
    existing_faq = usecases.faq.find_by_id_usecase.execute(faq_id)
    from src.core.platform.errors import NewApplicationError
    from src.core.platform.errors.mappings.faq import FAQUpdateNotFoundError

    if existing_faq is None:
        raise NewApplicationError(FAQUpdateNotFoundError)

    # Merge updates
    updated_data = existing_faq.dict()
    update_dict = faq_update.dict(exclude_unset=True, exclude_none=True)
    updated_data.update(update_dict)

    updated_faq_model = FAQ(**updated_data)
    result = usecases.faq.update_usecase.execute(faq_id, updated_faq_model, user_id)

    return FAQOutput.from_output(result)


@router.delete("/{faq_id}", status_code=status.HTTP_200_OK)
async def delete_faq(
    faq_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    """Delete a FAQ (only if it belongs to the authenticated user)"""
    user_id = request.state.user.get("user_id")
    result = usecases.faq.delete_usecase.execute(faq_id, user_id)
    return {"message": "FAQ deleted successfully", "id": faq_id, "deleted": result}
