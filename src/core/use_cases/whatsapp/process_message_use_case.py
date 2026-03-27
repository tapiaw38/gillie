from typing import Dict, Any, List
from src.core.platform.appcontext.appcontext import Factory
from src.core.domain import Profile, SenderEnum
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import ValidationError
from src.core.platform.logging import get_logger
from src.adapters.web.integrations.whatsapp.whatsapp import WhatsAppIntegration
from src.schemas import ConversationInput, MessageInput


class ProcessWhatsAppMessageUseCase:
    """
    Process incoming WhatsApp messages.
    Handles webhook payloads, creates/finds conversations, sends messages to AI,
    and returns responses to WhatsApp.
    """

    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, payload: Dict[Any, Any], profile: Profile, auth_token: str = None):
        """
        Execute the use case to process WhatsApp webhook messages.

        Args:
            payload: WhatsApp webhook payload
            profile: User profile
            auth_token: Optional JWT auth token for calendar API calls
        """
        logger = get_logger(__name__)
        context = self.context_factory()

        whatsapp_integration = None
        if profile.integrations:
            for integration in profile.integrations:
                if integration.name == "whatsapp" and integration.activated:
                    whatsapp_integration = integration
                    break

        if not whatsapp_integration:
            raise NewApplicationError(
                ValidationError,
                Exception("WhatsApp integration is not activated")
            )

        required_configs = ["accessToken", "phoneNumberId"]
        for config in required_configs:
            if (
                config not in whatsapp_integration.config
                or not whatsapp_integration.config[config]
            ):
                logger.error(f"WhatsApp configuration incomplete: missing {config}")
                raise NewApplicationError(
                    ValidationError,
                    Exception(f"WhatsApp configuration is not valid: missing {config}")
                )

        from src.core.use_cases.use_cases import Usecases

        try:
            wa_client = WhatsAppIntegration(
                access_token=whatsapp_integration.config["accessToken"],
                phone_number_id=whatsapp_integration.config["phoneNumberId"],
            )

            messages = wa_client.receive_message(payload)

            if not messages:
                return {"status": "success", "message": "There are no messages to process"}

            responses = []

            for msg in messages:
                sender_phone = msg["from"]
                message_id = msg["id"]
                msg_type = msg["type"]
                message_text = None

                if msg_type == "audio" and msg.get("audio"):
                    try:
                        logger.info(f"Processing audio message from {sender_phone}")

                        audio_id = msg["audio"]["id"]
                        audio_bytes = await wa_client.download_audio(audio_id)

                        stt_integration = context.integrations.stt
                        transcription_result = await stt_integration.audio_bytes_to_text(
                            audio_bytes=audio_bytes,
                            audio_format="ogg",  # WhatsApp uses OGG Opus format
                            settings={"language": "es-ES"}
                        )

                        if not transcription_result.get("success", False):
                            logger.warning(f"Transcription failed for audio {audio_id}")
                            message_text = "[Audio no pudo ser transcrito]"
                        else:
                            message_text = transcription_result["text"]
                            logger.info(
                                f"Audio transcribed successfully: '{message_text[:50]}...', "
                                f"method: {transcription_result.get('method')}"
                            )

                    except Exception as e:
                        logger.error(f"Error processing audio message: {str(e)}", exc_info=True)
                        message_text = "[Error procesando audio]"

                elif msg_type == "text" and msg.get("text"):
                    message_text = msg["text"]

                else:
                    logger.debug(f"Skipping unsupported message type: {msg_type}")
                    continue

                if not message_text:
                    logger.warning(f"No text content for message {message_id}")
                    continue

                conversation_list = context.repositories.conversation.find_user_id(
                    profile.user_id
                )

                conversation_id = None

                for conversation_data in conversation_list:
                    if f"WhatsApp-{sender_phone}" in conversation_data.title:
                        conversation_id = conversation_data.id
                        break

                if not conversation_id:
                    conversation_input = ConversationInput(
                        title=f"WhatsApp-{sender_phone}"
                    )

                    new_conversation = context.repositories.conversation.create(
                        conversation_input.dict(), profile.user_id
                    )

                    conversation_id = new_conversation

                from src.core.use_cases.conversation import AddMessageUseCase

                add_message_usecase = AddMessageUseCase(self.context_factory)

                message_input = MessageInput(
                    content=message_text,
                    context=(
                        "[CANAL: whatsapp] El usuario está chateando por WhatsApp. "
                        "Si el usuario pide una captura de pantalla o imagen de la pantalla, usa send_screenshot. "
                        "Si el usuario pide recibir un archivo, usa send_file."
                    ),
                )
                await add_message_usecase.execute(
                    conversation_id=conversation_id,
                    message=message_input,
                    sender=SenderEnum.user,
                    user_id=profile.user_id,
                    auth_token=auth_token,
                )

                updated_conversation = context.repositories.conversation.find_by_id(
                    conversation_id
                )

                all_messages = updated_conversation.messages

                last_user_idx = next(
                    (i for i in range(len(all_messages) - 1, -1, -1)
                     if all_messages[i].sender != SenderEnum.assistant),
                    None
                )

                new_assistant_messages = []
                if last_user_idx is not None:
                    new_assistant_messages = [
                        m for m in all_messages[last_user_idx + 1:]
                        if m.sender == SenderEnum.assistant
                    ]

                if new_assistant_messages:
                    logger.info(
                        f"Sending {len(new_assistant_messages)} AI message(s) to WhatsApp: "
                        f"phone={sender_phone}, message_id={message_id}"
                    )

                    from src.core.platform.utils.message_parser import parse_message_segments

                    last_sent = False
                    for assistant_msg in new_assistant_messages:
                        for segment in parse_message_segments(assistant_msg.content):
                            if segment["type"] == "image":
                                last_sent = wa_client.send_image(sender_phone, segment["content"])
                            elif segment["type"] == "document":
                                last_sent = wa_client.send_document(sender_phone, segment["content"])
                            elif segment["content"]:
                                last_sent = wa_client.send_message(sender_phone, segment["content"])
                        if not last_sent:
                            logger.warning(
                                f"Failed to send message to WhatsApp: phone={sender_phone}"
                            )

                    if last_sent:
                        logger.info(
                            f"All messages sent to WhatsApp: phone={sender_phone}"
                        )

                    last_msg = new_assistant_messages[-1]
                    responses.append(
                        {
                            "phone": sender_phone,
                            "message_id": message_id,
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
                        f"No assistant messages found to send as a response: conversation_id={conversation_id}"
                    )

            return {"status": "success", "processed_messages": responses}

        except Exception as e:
            logger.error(f"Error processing WhatsApp messages: {str(e)}")
            raise NewApplicationError(ValidationError, e)
