from typing import List, Optional
from src.core.domain import (
    Conversation,
    Message,
    Profile,
)
from src.adapters.datasources.datasources import Datasources
from pymongo.errors import PyMongoError


from .repository_interface import RepositoryInterface
from .create import create_conversation
from .find_by_id import find_conversation_by_id
from .find_user_id import find_conversations_by_user_id
from .update_profile_by_user_id import update_profile_by_user_id
from .update_messages_by_id import update_messages_by_id


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.client = datasources.no_sql_conversations_client

    def create(self, conversation: Conversation) -> str:
        return create_conversation(self.client, conversation)

    def find_by_id(self, id: str) -> Optional[Conversation]:
        return find_conversation_by_id(self.client, id)

    def find_user_id(self, user_id: str) -> List[Conversation]:
        return find_conversations_by_user_id(self.client, user_id)

    def update_profile_by_user_id(self, user_id: str, profile: Profile) -> str:
        return update_profile_by_user_id(self.client, user_id, profile)

    def update_messages_by_id(self, id: str, messages: List[Message]) -> None:
        update_messages_by_id(self.client, id, messages)
