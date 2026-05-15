import asyncio
from typing import Any, Dict

from src.core.domain import Profile, SenderEnum
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import ValidationError
from src.core.platform.errors.mappings.teams import TeamsProcessMessageError
from src.core.platform.logging import get_logger
from src.schemas import ConversationInput, MessageInput


class ProcessTeamsMessageUseCase:
    """
    Process incoming Teams Bot Framework messages using the shared conversation pipeline.
    """

    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, payload: Dict[str, Any], profile: Profile):
        logger = get_logger(__name__)
        context = self.context_factory()

        teams_integration = None
        if profile.integrations:
            for integration in profile.integrations:
                if integration.name == "teams" and integration.activated:
                    teams_integration = integration
                    break

        if not teams_integration:
            raise NewApplicationError(
                ValidationError,
                Exception("Teams integration is not activated"),
            )

        app_id = teams_integration.config.get("app_id", "")
        app_password = teams_integration.config.get("app_password", "")
        if not app_id or not app_password:
            raise NewApplicationError(
                ValidationError,
                Exception("Teams configuration is not valid: missing app_id or app_password"),
            )

        try:
            teams_client = context.integrations.make_teams_client(app_id, app_password)
            messages = await asyncio.to_thread(teams_client.receive_message, payload)

            if not messages:
                return {"status": "success", "message": "No messages to process"}

            responses = []

            for msg in messages:
                service_url = msg["service_url"]
                teams_conv_id = msg["conversation_id"]
                activity_id = msg["activity_id"]
                user_id_teams = msg["user_id"]
                user_name = msg["user_name"]
                bot_id = msg.get("bot_id", "")
                tenant_id = msg.get("tenant_id", "")
                message_text = msg["text"]

                conversation_list = await context.repositories.conversation.find_user_id(profile.user_id)
                conversation_key = f"Teams-{tenant_id or 'global'}-{teams_conv_id}"

                conversation_id = None
                for conv in conversation_list:
                    if conv.title == conversation_key:
                        conversation_id = conv.id
                        break

                if not conversation_id:
                    from src.core.use_cases.conversation import CreateUseCase

                    create_usecase = CreateUseCase(self.context_factory)
                    new_conv = await create_usecase.execute(
                        ConversationInput(title=conversation_key),
                        profile.user_id,
                    )
                    conversation_id = new_conv.data.id

                if tenant_id and (
                    not teams_integration.config.get("tenant_id")
                    or not teams_integration.config.get("bot_id")
                    or not teams_integration.config.get("service_url")
                ):
                    teams_integration.config["tenant_id"] = tenant_id
                    if bot_id:
                        teams_integration.config["bot_id"] = bot_id
                    if service_url:
                        teams_integration.config["service_url"] = service_url
                    await context.repositories.profile.update_integrations(profile.user_id, profile.integrations)
                    await context.repositories.conversation.update_profile_by_user_id(
                        profile.user_id,
                        profile=profile,
                    )

                from src.core.use_cases.conversation import AddMessageUseCase

                add_message_usecase = AddMessageUseCase(self.context_factory)
                message_input = MessageInput(
                    content=message_text,
                    context=(
                        "[CANAL: teams] El usuario está chateando por Microsoft Teams. "
                        "Respondé de forma apta para chat corporativo. "
                        "Si el usuario pide recibir un archivo, usa send_file."
                    ),
                )
                await add_message_usecase.execute(
                    conversation_id=conversation_id,
                    message=message_input,
                    sender=SenderEnum.user,
                    user_id=profile.user_id,
                )

                updated_conversation = await context.repositories.conversation.find_by_id(conversation_id)
                all_messages = updated_conversation.messages

                last_user_idx = next(
                    (
                        i for i in range(len(all_messages) - 1, -1, -1)
                        if all_messages[i].sender != SenderEnum.assistant
                    ),
                    None,
                )

                new_assistant_messages = []
                if last_user_idx is not None:
                    new_assistant_messages = [
                        m for m in all_messages[last_user_idx + 1:]
                        if m.sender == SenderEnum.assistant
                    ]

                if not new_assistant_messages:
                    logger.warning(f"[teams] No assistant messages for conversation {conversation_id}")
                    continue

                last_sent = False
                for assistant_msg in new_assistant_messages:
                    last_sent = bool(
                        await asyncio.to_thread(
                            teams_client.send_message,
                            service_url,
                            teams_conv_id,
                            assistant_msg.content,
                            activity_id,
                        )
                    )

                last_msg = new_assistant_messages[-1]
                responses.append(
                    {
                        "teams_conversation_id": teams_conv_id,
                        "user_id": user_id_teams,
                        "response_sent": last_sent,
                        "message": (
                            last_msg.content[:100] + "..."
                            if len(last_msg.content) > 100
                            else last_msg.content
                        ),
                        "user_name": user_name,
                    }
                )

            return {"status": "success", "processed_messages": responses}

        except Exception as e:
            logger.error(f"Error processing Teams message: {e}", exc_info=True)
            raise NewApplicationError(TeamsProcessMessageError, e)
