from pydantic import BaseModel
from typing import Optional, List


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
