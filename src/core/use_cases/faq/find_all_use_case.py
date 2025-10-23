from src.core.domain import FAQ
from typing import List, Optional
from src.core.platform.appcontext.appcontext import Factory


class FindAllUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, category: Optional[str] = None, is_active: Optional[bool] = None) -> List[FAQ]:
        faqs = self.context_factory.repositories.faq.find_all(category, is_active)
        return faqs
