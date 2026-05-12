from src.schemas import MessageListOutput
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import ConversationGetNotFoundError
from src.core.platform.errors.mappings.common import ForbiddenError


class DeleteAllMessagesUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, conversation_id: str, user_id: str):
        context = self.context_factory()
        search_conversation = await context.repositories.conversation.find_by_id(conversation_id)
        if not search_conversation:
            raise NewApplicationError(ConversationGetNotFoundError)

        if user_id != search_conversation.profile.user_id:
            raise NewApplicationError(ForbiddenError)

        await context.repositories.conversation.update_messages_by_id(
            conversation_id,
            [],
        )

        search_conversation.messages = []

        return MessageListOutput.from_output(search_conversation.messages)
