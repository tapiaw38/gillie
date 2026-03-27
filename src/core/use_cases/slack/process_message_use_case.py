from typing import Dict, Any

from src.core.platform.appcontext.appcontext import Factory
from src.core.domain import Profile, SenderEnum
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import ValidationError
from src.core.platform.logging import get_logger
from src.adapters.web.integrations.slack.slack import SlackIntegration
from src.schemas import ConversationInput, MessageInput


class ProcessSlackMessageUseCase:
    """
    Process incoming Slack messages received via the Events API.

    Handles event_callback payloads, creates or reuses per-channel
    conversations, sends the user message through the AI pipeline,
    and delivers the assistant's reply back to the originating Slack channel.
    """

    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, payload: Dict[Any, Any], profile: Profile):
        """
        Execute the use case to process a Slack Events API message.

        Args:
            payload: Slack event_callback payload
            profile: User profile that owns the active Slack integration
        """
        logger = get_logger(__name__)
        context = self.context_factory()

        slack_integration = None
        if profile.integrations:
            for integration in profile.integrations:
                if integration.name == "slack" and integration.activated:
                    slack_integration = integration
                    break

        if not slack_integration:
            raise NewApplicationError(
                ValidationError,
                Exception("Slack integration is not activated"),
            )

        required_configs = ["bot_token"]
        for config_key in required_configs:
            if (
                config_key not in slack_integration.config
                or not slack_integration.config[config_key]
            ):
                logger.error(f"Slack configuration incomplete: missing {config_key}")
                raise NewApplicationError(
                    ValidationError,
                    Exception(f"Slack configuration is not valid: missing {config_key}"),
                )

        try:
            slack_client = SlackIntegration(
                bot_token=slack_integration.config["bot_token"],
                signing_secret=slack_integration.config.get("signing_secret", ""),
            )

            messages = slack_client.receive_message(payload)

            if not messages:
                return {"status": "success", "message": "There are no messages to process"}

            responses = []

            for msg in messages:
                channel = msg["channel"]
                user_id = msg["user_id"]
                message_text = msg["text"]
                ts = msg["ts"]

                if not message_text:
                    logger.warning(
                        f"Empty text for Slack message: user_id={user_id}, channel={channel}"
                    )
                    continue

                conversation_list = context.repositories.conversation.find_user_id(
                    profile.user_id
                )

                conversation_id = None
                conversation_title = f"Slack-{channel}"

                for conversation_data in conversation_list:
                    if conversation_title in conversation_data.title:
                        conversation_id = conversation_data.id
                        break

                if not conversation_id:
                    conversation_input = ConversationInput(title=conversation_title)
                    conversation_id = context.repositories.conversation.create(
                        conversation_input.dict(), profile.user_id
                    )

                from src.core.use_cases.conversation import AddMessageUseCase

                add_message_usecase = AddMessageUseCase(self.context_factory)

                message_input = MessageInput(
                    content=message_text,
                    context=(
                        "[CANAL: slack] El usuario está chateando por Slack. "
                        "Si el usuario pide una captura de pantalla o imagen de la pantalla, usa send_screenshot. "
                        "Si el usuario pide recibir un archivo, usa send_file."
                    ),
                )
                await add_message_usecase.execute(
                    conversation_id=conversation_id,
                    message=message_input,
                    sender=SenderEnum.user,
                    user_id=profile.user_id,
                )

                updated_conversation = context.repositories.conversation.find_by_id(
                    conversation_id
                )

                all_messages = updated_conversation.messages

                last_user_idx = next(
                    (
                        i
                        for i in range(len(all_messages) - 1, -1, -1)
                        if all_messages[i].sender != SenderEnum.assistant
                    ),
                    None,
                )

                new_assistant_messages = []
                if last_user_idx is not None:
                    new_assistant_messages = [
                        m
                        for m in all_messages[last_user_idx + 1:]
                        if m.sender == SenderEnum.assistant
                    ]

                if new_assistant_messages:
                    logger.info(
                        f"Sending {len(new_assistant_messages)} AI message(s) to Slack: "
                        f"channel={channel}, ts={ts}"
                    )

                    from src.core.platform.utils.message_parser import parse_message_segments

                    last_sent = False
                    for assistant_msg in new_assistant_messages:
                        for segment in parse_message_segments(assistant_msg.content):
                            if segment["type"] == "image":
                                last_sent = slack_client.send_image(channel, segment["content"])
                            elif segment["type"] == "document":
                                last_sent = slack_client.send_document(channel, segment["content"])
                            elif segment["content"]:
                                last_sent = slack_client.send_message(channel, segment["content"])

                    if not last_sent:
                        logger.warning(f"Failed to send message to Slack: channel={channel}")
                    else:
                        logger.info(f"All messages sent to Slack: channel={channel}")

                    last_msg = new_assistant_messages[-1]
                    responses.append(
                        {
                            "channel": channel,
                            "user_id": user_id,
                            "response_sent": last_sent,
                            "message": (
                                last_msg.content[:100] + "..."
                                if len(last_msg.content) > 100
                                else last_msg.content
                            ),
                        }
                    )
                else:
                    logger.warning(
                        f"No assistant messages found to send as a response: "
                        f"conversation_id={conversation_id}"
                    )

            return {"status": "success", "processed_messages": responses}

        except Exception as e:
            logger.error(f"Error processing Slack messages: {str(e)}", exc_info=True)
            raise NewApplicationError(ValidationError, e)
