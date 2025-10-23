from src.core.domain import FAQ
from typing import List
from src.core.platform.appcontext.appcontext import Factory


class FindByCategoryUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, category: str) -> List[FAQ]:
        faqs = self.context_factory.repositories.faq.find_by_category(category)
        return faqs
