from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from src.core.domain import FAQ


class FAQInput(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = True
    order: Optional[int] = 0


class FAQUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    order: Optional[int] = None


class FAQOutputData(BaseModel):
    id: Optional[str]
    profile_id: str
    question: str
    answer: str
    category: Optional[str]
    tags: Optional[List[str]]
    is_active: Optional[bool]
    order: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class FAQOutput(BaseModel):
    data: FAQOutputData

    @staticmethod
    def from_output(faq: FAQ):
        return FAQOutput(
            data=FAQOutputData(
                id=faq.id,
                profile_id=faq.profile_id,
                question=faq.question,
                answer=faq.answer,
                category=faq.category,
                tags=faq.tags,
                is_active=faq.is_active,
                order=faq.order,
                created_at=faq.created_at,
                updated_at=faq.updated_at,
            )
        )


class FAQListOutput(BaseModel):
    data: List[FAQOutputData]

    @staticmethod
    def from_output(faqs: List[FAQ]):
        return FAQListOutput(
            data=[
                FAQOutput.from_output(faq).data
                for faq in faqs
            ]
        )
