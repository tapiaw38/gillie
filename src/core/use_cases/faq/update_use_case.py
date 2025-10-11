from src.core.domain import FAQ
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory


class UpdateUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, faq_id: str, faq: FAQ) -> FAQ:
        try:
            existing_faq = self.context_factory.repositories.faq.find_by_id(faq_id)
            if not existing_faq:
                raise Exception(f"FAQ with id {faq_id} not found")

            self.context_factory.repositories.faq.update(faq_id, faq)

            updated_faq = self.context_factory.repositories.faq.find_by_id(faq_id)
            if not updated_faq:
                raise Exception("Error: FAQ not found after update")

            return updated_faq

        except PyMongoError as e:
            raise Exception(f"Error interacting with database: {e}")

        except Exception as e:
            raise Exception(f"Error executing UpdateUseCase: {e}")
