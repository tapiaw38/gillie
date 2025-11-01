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

    async def execute(self, payload: Dict[Any, Any], profile: Profile):
        """
        Execute the use case to process WhatsApp webhook messages.
        """
        logger = get_logger(__name__)
        context = self.context_factory.create()

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

                conversation_list = context.repositories.conversation.find_by_user_id(
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

                message_input = MessageInput(content=message_text, context=None)
                await add_message_usecase.execute(
                    conversation_id=conversation_id,
                    message=message_input,
                    sender=SenderEnum.user,
                    user_id=profile.user_id,
                )

                updated_conversation = context.repositories.conversation.find_by_id(
                    conversation_id
                )

                assistant_messages = [
                    msg
                    for msg in updated_conversation.messages
                    if msg.sender == SenderEnum.assistant
                ]

                if assistant_messages:
                    last_assistant_message = assistant_messages[-1]

                    logger.info(
                        f"Sending AI response to WhatsApp: phone={sender_phone}, message_id={message_id}"
                    )

                    sent = wa_client.send_message(
                        sender_phone, last_assistant_message.content
                    )

                    if sent:
                        logger.info(
                            f"Response successfully sent to WhatsApp: phone={sender_phone}"
                        )
                    else:
                        logger.warning(
                            f"Failed to send response to WhatsApp: phone={sender_phone}"
                        )

                    responses.append(
                        {
                            "phone": sender_phone,
                            "message_id": message_id,
                            "response_sent": sent,
                            "message": (
                                last_assistant_message.content[:100] + "..."
                                if len(last_assistant_message.content) > 100
                                else last_assistant_message.content
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
