from src.core.domain import FAQ
from typing import List
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory


class FindByCategoryUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, category: str) -> List[FAQ]:
        try:
            faqs = self.context_factory.repositories.faq.find_by_category(category)
            return faqs

        except PyMongoError as e:
            raise Exception(f"Error interacting with database: {e}")

        except Exception as e:
            raise Exception(f"Error executing FindByCategoryUseCase: {e}")
