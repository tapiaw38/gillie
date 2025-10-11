from fastapi import APIRouter, status, Depends, HTTPException, Query
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
    service: Services = Depends(get_instance)
):
    """Create a new FAQ"""
    created_faq = await service.faq.create(faq)
    return created_faq


@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_faqs(
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    service: Services = Depends(get_instance)
):
    """Get all FAQs, optionally filtered by category and/or active status"""
    faqs = await service.faq.find_all(category, is_active)
    return faqs


@router.get("/{faq_id}", status_code=status.HTTP_200_OK)
async def get_faq_by_id(
    faq_id: str,
    service: Services = Depends(get_instance)
):
    """Get a specific FAQ by ID"""
    faq = await service.faq.find_by_id(faq_id)
    if faq is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FAQ with id {faq_id} not found"
        )
    return faq


@router.get("/category/{category}", status_code=status.HTTP_200_OK)
async def get_faqs_by_category(
    category: str,
    service: Services = Depends(get_instance)
):
    """Get all active FAQs for a specific category"""
    faqs = await service.faq.find_by_category(category)
    return faqs


@router.put("/{faq_id}", status_code=status.HTTP_200_OK)
async def update_faq(
    faq_id: str,
    faq: FAQUpdate,
    service: Services = Depends(get_instance)
):
    """Update an existing FAQ"""
    updated_faq = await service.faq.update(faq_id, faq)
    return updated_faq


@router.delete("/{faq_id}", status_code=status.HTTP_200_OK)
async def delete_faq(
    faq_id: str,
    service: Services = Depends(get_instance)
):
    """Delete a FAQ"""
    result = await service.faq.delete(faq_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FAQ with id {faq_id} not found"
        )
    return {"message": "FAQ deleted successfully", "id": faq_id}
