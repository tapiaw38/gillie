from src.core.domain import FAQ
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.faq import (
    FAQUpdateNotFoundError,
    FAQGetNotFoundError
)


class UpdateUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, faq_id: str, faq: FAQ) -> FAQ:
        existing_faq = self.context_factory.repositories.faq.find_by_id(faq_id)
        if not existing_faq:
            raise NewApplicationError(FAQUpdateNotFoundError)

        self.context_factory.repositories.faq.update(faq_id, faq)

        updated_faq = self.context_factory.repositories.faq.find_by_id(faq_id)
        if not updated_faq:
            raise NewApplicationError(FAQGetNotFoundError)

        return updated_faq
