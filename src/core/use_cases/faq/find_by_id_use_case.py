from src.core.domain import FAQ
from typing import Optional
from src.core.platform.appcontext.appcontext import Factory


class FindByIdUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, faq_id: str) -> Optional[FAQ]:
        faq = self.context_factory.repositories.faq.find_by_id(faq_id)
        return faq
