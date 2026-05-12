from typing import Dict, Any
from src.core.platform.appcontext.appcontext import Factory
from src.core.domain import Profile, SenderEnum
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import ValidationError
from src.core.platform.logging import get_logger
from src.schemas import ConversationInput, MessageInput


class ProcessTelegramMessageUseCase:
    """
    Process incoming Telegram messages.
    Handles webhook updates, creates/finds conversations, sends messages to AI,
    and returns responses to Telegram.
    """

    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, payload: Dict[str, Any], profile: Profile):
        logger = get_logger(__name__)
        context = self.context_factory()

        telegram_integration = None
        if profile.integrations:
            for integration in profile.integrations:
                if integration.name == "telegram" and integration.activated:
                    telegram_integration = integration
                    break

        if not telegram_integration:
            raise NewApplicationError(
                ValidationError,
                Exception("Telegram integration is not activated"),
            )

        bot_token = telegram_integration.config.get("bot_token")
        if not bot_token:
            raise NewApplicationError(
                ValidationError,
                Exception("Telegram configuration is not valid: missing bot_token"),
            )

        try:
            tg_client = context.integrations.make_telegram_client(
                bot_token=bot_token,
                secret_token=telegram_integration.config.get("secret_token", ""),
                store_service=context.store_service,
            )

            messages = tg_client.receive_message(payload)

            if not messages:
                return {"status": "success", "message": "No messages to process"}

            responses = []

            for msg in messages:
                chat_id = msg["chat_id"]
                message_text = None

                if msg.get("voice"):
                    try:
                        voice_data = msg["voice"]
                        file_id = voice_data.get("file_id")
                        audio_bytes = tg_client.download_voice(file_id)
                        if audio_bytes:
                            stt_integration = context.integrations.stt
                            result = await stt_integration.audio_bytes_to_text(
                                audio_bytes=audio_bytes,
                                audio_format="ogg",
                                settings={"language": "es-ES"},
                            )
                            if result.get("success"):
                                message_text = result["text"]
                            else:
                                message_text = "[Audio no pudo ser transcrito]"
                        else:
                            message_text = "[Error descargando audio]"
                    except Exception as e:
                        logger.error(f"[telegram] Error processing voice: {e}", exc_info=True)
                        message_text = "[Error procesando audio]"

                elif msg.get("text"):
                    message_text = msg["text"]

                else:
                    logger.debug(f"[telegram] Skipping unsupported message type for chat {chat_id}")
                    continue

                if not message_text:
                    continue

                conversation_list = await context.repositories.conversation.find_user_id(profile.user_id)

                conversation_id = None
                for conv in conversation_list:
                    if f"Telegram-{chat_id}" in conv.title:
                        conversation_id = conv.id
                        break

                if not conversation_id:
                    from src.core.use_cases.conversation import CreateUseCase
                    create_usecase = CreateUseCase(self.context_factory)
                    new_conv = await create_usecase.execute(
                        ConversationInput(title=f"Telegram-{chat_id}"),
                        profile.user_id,
                    )
                    conversation_id = new_conv.data.id

                tg_client.send_typing_action(chat_id)

                from src.core.use_cases.conversation import AddMessageUseCase

                add_message_usecase = AddMessageUseCase(self.context_factory)
                message_input = MessageInput(
                    content=message_text,
                    context=(
                        "[CANAL: telegram] El usuario está chateando por Telegram. "
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

                updated_conversation = await context.repositories.conversation.find_by_id(conversation_id)
                all_messages = updated_conversation.messages

                last_user_idx = next(
                    (i for i in range(len(all_messages) - 1, -1, -1)
                     if all_messages[i].sender != SenderEnum.assistant),
                    None,
                )

                new_assistant_messages = []
                if last_user_idx is not None:
                    new_assistant_messages = [
                        m for m in all_messages[last_user_idx + 1:]
                        if m.sender == SenderEnum.assistant
                    ]

                if new_assistant_messages:
                    from src.core.platform.utils.message_parser import parse_message_segments

                    last_sent = False
                    for assistant_msg in new_assistant_messages:
                        logger.info(f"[telegram] assistant msg content (len={len(assistant_msg.content)}): {assistant_msg.content!r}")
                        segments = parse_message_segments(assistant_msg.content)
                        logger.info(f"[telegram] parsed segments: {segments}")
                        for segment in segments:
                            if segment["type"] == "image":
                                url = segment["content"]
                                # Verify local files exist before sending to avoid hallucinated URLs
                                if tg_client._is_local_url(url):
                                    store = getattr(context, "store_service", None)
                                    base_url = getattr(store, "base_url", None)
                                    if base_url and url.startswith(base_url):
                                        key = url[len(base_url):].lstrip("/")
                                        try:
                                            store.get_object(key)
                                        except Exception:
                                            logger.warning(f"[telegram] Skipping hallucinated image URL (file not found): {url}")
                                            continue
                                last_sent = tg_client.send_image(chat_id, url)
                            elif segment["type"] == "document":
                                last_sent = tg_client.send_document(chat_id, segment["content"])
                            elif segment["content"]:
                                last_sent = tg_client.send_message(chat_id, segment["content"])
                        if not last_sent:
                            logger.warning(f"[telegram] Failed to send message to chat {chat_id}")

                    last_msg = new_assistant_messages[-1]
                    responses.append({
                        "chat_id": chat_id,
                        "response_sent": last_sent,
                        "message": last_msg.content[:100] + "..." if len(last_msg.content) > 100 else last_msg.content,
                    })
                else:
                    logger.warning(f"[telegram] No assistant messages for conversation {conversation_id}")

            return {"status": "success", "processed_messages": responses}

        except Exception as e:
            logger.error(f"[telegram] Error processing messages: {e}")
            raise NewApplicationError(ValidationError, e)
