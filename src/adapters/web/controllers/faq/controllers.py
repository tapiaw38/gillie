from fastapi import APIRouter, status, Depends, Request, Query
from src.schemas import (
    FAQInput,
    FAQUpdate,
    FAQOutput,
    FAQListOutput,
)
from src.adapters.services.services import Services
from typing import Optional


router = APIRouter(
    prefix="/faq",
    tags=["FAQ"],
)


def get_instance() -> Services:
    return Services.get_instance()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_faq(
    faq: FAQInput,
    request: Request,
    service: Services = Depends(get_instance)
):
    """Create a new FAQ"""
    user_id = request.state.user.get("user_id")
    created_faq = await service.faq.create(faq, user_id)
    return created_faq


@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_faqs(
    request: Request,
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    service: Services = Depends(get_instance)
):
    """Get all FAQs for the authenticated user, optionally filtered by category and/or active status"""
    user_id = request.state.user.get("user_id")
    faqs = await service.faq.find_all(user_id, category, is_active)
    return faqs


@router.get("/{faq_id}", status_code=status.HTTP_200_OK)
async def get_faq_by_id(
    faq_id: str,
    service: Services = Depends(get_instance)
):
    """Get a specific FAQ by ID"""
    faq = await service.faq.find_by_id(faq_id)
    if faq is None:
        from src.core.platform.errors import NewApplicationError
        from src.core.platform.errors.mappings.faq import FAQGetNotFoundError
        raise NewApplicationError(FAQGetNotFoundError)
    return faq


@router.get("/category/{category}", status_code=status.HTTP_200_OK)
async def get_faqs_by_category(
    category: str,
    request: Request,
    service: Services = Depends(get_instance)
):
    """Get all active FAQs for the authenticated user in a specific category"""
    user_id = request.state.user.get("user_id")
    faqs = await service.faq.find_by_category(user_id, category)
    return faqs


@router.put("/{faq_id}", status_code=status.HTTP_200_OK)
async def update_faq(
    faq_id: str,
    faq: FAQUpdate,
    request: Request,
    service: Services = Depends(get_instance)
):
    """Update an existing FAQ (only if it belongs to the authenticated user)"""
    user_id = request.state.user.get("user_id")
    updated_faq = await service.faq.update(faq_id, faq, user_id)
    return updated_faq


@router.delete("/{faq_id}", status_code=status.HTTP_200_OK)
async def delete_faq(
    faq_id: str,
    request: Request,
    service: Services = Depends(get_instance)
):
    """Delete a FAQ (only if it belongs to the authenticated user)"""
    user_id = request.state.user.get("user_id")
    result = await service.faq.delete(faq_id, user_id)
    return {"message": "FAQ deleted successfully", "id": faq_id, "deleted": result}
