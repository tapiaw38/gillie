from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FAQInput(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None


class FAQUpdate(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None


class FAQData(BaseModel):
    id: str
    category: str
    question: str
    answer: str


class FAQListOutput(BaseModel):
    data: List[FAQData]


class FAQOutput(BaseModel):
    data: FAQData


class SkillData(BaseModel):
    name: str


class SkillListOutput(BaseModel):
    data: List[SkillData]


class SkillContentOutput(BaseModel):
    name: str
    content: str


class GeneralMemoryOutput(BaseModel):
    content: str


class ExtractMemoryOutput(BaseModel):
    extracted: int
    status: str


class MemoryRootOutput(BaseModel):
    content: str


class MemoryRootInput(BaseModel):
    content: str


class MemoryResolvedOutput(BaseModel):
    content: str


class OwnerMemoryData(BaseModel):
    id: str
    owner_user_id: Optional[str] = None
    memory_scope_id: Optional[str] = None
    source_conversation_id: Optional[str] = None
    content: str
    importance: int
    emotion: Optional[str] = None
    tags: List[str]
    created_at: datetime


class OwnerMemoryListOutput(BaseModel):
    data: List[OwnerMemoryData]
    has_more: bool = False
    next_offset: Optional[int] = None
