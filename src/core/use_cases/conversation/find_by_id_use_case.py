from src.schemas import ConversationOutput
from src.core.domain import Conversation
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import ConversationGetNotFoundError
from typing import Optional


class FindByIdUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, conversation_id: str) -> Optional[Conversation]:
        conversation = self.context_factory.repositories.conversation.find_by_id(
            conversation_id
        )
        if not conversation:
            raise NewApplicationError(ConversationGetNotFoundError)
        return ConversationOutput.from_output(conversation)