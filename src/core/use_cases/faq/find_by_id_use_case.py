from src.core.domain import FAQ
from typing import Optional
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory


class FindByIdUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, faq_id: str) -> Optional[FAQ]:
        try:
            faq = self.context_factory.repositories.faq.find_by_id(faq_id)
            return faq

        except PyMongoError as e:
            raise Exception(f"Error interacting with database: {e}")

        except Exception as e:
            raise Exception(f"Error executing FindByIdUseCase: {e}")
