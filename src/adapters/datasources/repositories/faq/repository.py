from src.adapters.datasources.datasources import Datasources
from .repository_interface import RepositoryInterface
from src.core.domain import FAQ
from typing import List, Optional
from pymongo.errors import PyMongoError

from .create import create_faq
from .find_by_id import find_faq_by_id
from .find_all import find_all_faqs
from .update import update_faq
from .delete import delete_faq
from .find_by_category import find_faqs_by_category


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.client = datasources.no_sql_faqs_client
        self.client.create_index("category")
        self.client.create_index("order")
        self.client.create_index("is_active")

    def create(self, faq: FAQ) -> str:
        return create_faq(self.client, faq)

    def find_by_id(self, id: str) -> Optional[FAQ]:
        return find_faq_by_id(self.client, id)

    def find_all(self, category: Optional[str] = None, is_active: Optional[bool] = None) -> List[FAQ]:
        return find_all_faqs(self.client, category, is_active)

    def update(self, id: str, faq: FAQ) -> str:
        return update_faq(self.client, id, faq)

    def delete(self, id: str) -> bool:
        return delete_faq(self.client, id)

    def find_by_category(self, category: str) -> List[FAQ]:
        return find_faqs_by_category(self.client, category)
