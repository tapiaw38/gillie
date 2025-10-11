from src.schemas import ConversationInput, ConversationOutput
from src.core.domain import Conversation, Profile
from datetime import datetime, timezone
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory
from uuid import uuid4


class CreateUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, conversation: ConversationInput, user_id: str) -> Conversation:
        try:
            profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
            generated_id = str(uuid4())
            generated_client_id = str(uuid4())
            new_conversation = Conversation(
                _id=generated_id,
                profile=Profile(
                    _id=profile.id,
                    user_id=profile.user_id,
                    assistant_name=profile.assistant_name,
                    business_name=profile.business_name,
                    functions=profile.functions,
                    business_context=profile.business_context,
                    role=profile.role,
                    files=profile.files,
                    created_at=profile.created_at,
                    updated_at=profile.updated_at,
                ),
                title=conversation.title,
                created_at=datetime.now(timezone.utc),
                client_id=generated_client_id,
                is_sandbox=conversation.is_sandbox,
            )

            conversation_id = self.context_factory.repositories.conversation.create(
                new_conversation
            )

            created_conversation = (
                self.context_factory.repositories.conversation.find_by_id(
                    conversation_id
                )
            )

            if not created_conversation:
                raise Exception("Error: conversation not found after creation")

            return ConversationOutput.from_output(created_conversation)

        except PyMongoError as e:
            raise Exception(f"Error interacting with database: {e}")

        except Exception as e:
            raise Exception(f"Error executing CreateUseCase: {e}")