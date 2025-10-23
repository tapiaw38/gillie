from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.faq import FAQDeleteNotFoundError


class DeleteUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, faq_id: str) -> bool:
        existing_faq = self.context_factory.repositories.faq.find_by_id(faq_id)
        if not existing_faq:
            raise NewApplicationError(FAQDeleteNotFoundError)

        deleted = self.context_factory.repositories.faq.delete(faq_id)
        return deleted
