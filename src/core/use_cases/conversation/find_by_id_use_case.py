from src.schemas import ConversationOutput
from src.core.domain import Conversation
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory
from typing import Optional


class FindByIdUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, conversation_id: str) -> Optional[Conversation]:
        try:
            conversation = self.context_factory.repositories.conversation.find_by_id(
                conversation_id
            )
            if not conversation:
                raise Exception("Conversation not found")
            return ConversationOutput.from_output(conversation)
        except PyMongoError as e:
            raise Exception(f"Error interacting with database: {e}")

        except Exception as e:
            raise Exception(f"Error executing FindByIdUseCase: {e}")