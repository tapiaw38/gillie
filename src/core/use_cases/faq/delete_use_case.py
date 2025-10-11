from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory


class DeleteUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, faq_id: str) -> bool:
        try:
            existing_faq = self.context_factory.repositories.faq.find_by_id(faq_id)
            if not existing_faq:
                raise Exception(f"FAQ with id {faq_id} not found")

            deleted = self.context_factory.repositories.faq.delete(faq_id)
            return deleted

        except PyMongoError as e:
            raise Exception(f"Error interacting with database: {e}")

        except Exception as e:
            raise Exception(f"Error executing DeleteUseCase: {e}")
