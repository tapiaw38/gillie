from src.schemas import ConversationListOutput
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory


class FindByUserIdUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str):
        try:
            conversations = self.context_factory.repositories.conversation.find_user_id(
                user_id
            )
            return ConversationListOutput.from_output(conversations)
        except PyMongoError as e:
            raise Exception(f"Error interacting with database: {e}")

        except Exception as e:
            raise Exception(f"Error executing FindByUserIdUseCase: {e}")