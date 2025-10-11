from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory


class DeleteUseCase:
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
                raise Exception("User not authorized to delete conversation")

            self.context_factory.repositories.conversation.delete_by_id(
                conversation_id
            )

            return {"message": "Conversation deleted successfully", "id": conversation_id}

        except PyMongoError as e:
            raise Exception(f"Error interacting with the database: {e}")

        except Exception as e:
            raise Exception(f"Error executing DeleteUseCase: {e}")
