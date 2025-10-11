from src.core.domain import FAQ
from datetime import datetime
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory
from uuid import uuid4


class CreateUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, faq: FAQ) -> FAQ:
        try:
            all_faqs = self.context_factory.repositories.faq.find_all()
            max_order = max([f.order for f in all_faqs], default=-1)
            next_order = max_order + 1

            generated_id = str(uuid4())
            new_faq = FAQ(
                _id=generated_id,
                question=faq.question,
                answer=faq.answer,
                category=faq.category,
                tags=faq.tags,
                is_active=faq.is_active if faq.is_active is not None else True,
                order=next_order,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            faq_id = self.context_factory.repositories.faq.create(new_faq)
            created_faq = self.context_factory.repositories.faq.find_by_id(faq_id)

            if not created_faq:
                raise Exception("Error: FAQ not found after creation")

            return created_faq

        except PyMongoError as e:
            raise Exception(f"Error interacting with database: {e}")

        except Exception as e:
            raise Exception(f"Error executing CreateUseCase: {e}")
