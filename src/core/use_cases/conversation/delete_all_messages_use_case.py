from src.schemas import MessageListOutput
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory


class DeleteAllMessagesUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    async def execute(self, conversation_id: str, user_id: str):
        try:
            search_conversation = (
                self.context_factory.repositories.conversation.find_by_id(
                    conversation_id
                )
            )
            if not search_conversation:
                raise Exception("Conversation not found")

            if user_id != search_conversation.profile.user_id:
                raise Exception("User not authorized to delete messages")

            self.context_factory.repositories.conversation.update_messages_by_id(
                conversation_id,
                [],
            )

            search_conversation.messages = []

            return MessageListOutput.from_output(search_conversation.messages)

        except PyMongoError as e:
            raise Exception(f"Error interacting with the database: {e}")

        except Exception as e:
            raise Exception(f"Error executing DeleteAllMessagesUseCase: {e}")