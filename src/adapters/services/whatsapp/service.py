from fastapi import HTTPException, status
from src.schemas import MessageInput
from src.core.domain import SenderEnum, Profile
from src.adapters.web.integrations.whatsapp.whatsapp import WhatsAppIntegration
from src.adapters.services.conversation.service import ConversationService
from src.core.platform.logging import get_logger
from typing import Dict, Any, List, Optional


class WhatsAppService:
    def __init__(self, conversation_service: ConversationService):
        self.conversation_service = conversation_service

    async def process_message(self, payload: Dict[Any, Any], profile: Profile):
        logger = get_logger(__name__)

        whatsapp_integration = None

        if profile.integrations:
            for integration in profile.integrations:
                if integration.name == "whatsapp" and integration.activated:
                    whatsapp_integration = integration
                    break

        if not whatsapp_integration:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="WhatsApp integration is not activated",
            )

        required_configs = ["accessToken", "phoneNumberId"]
        for config in required_configs:
            if (
                config not in whatsapp_integration.config
                or not whatsapp_integration.config[config]
            ):
                logger.error(f"WhatsApp configuration incomplete: missing {config}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"WhatsApp configuration is not valid: missing {config}",
                )

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
                if msg["type"] != "text" or not msg["text"]:
                    continue

                sender_phone = msg["from"]
                message_text = msg["text"]
                message_id = msg["id"]

                conversation_list = await self.conversation_service.find_by_user_id(
                    profile.user_id
                )

                conversation_id = None

                for conversation_data in conversation_list.data:
                    if f"WhatsApp-{sender_phone}" in conversation_data.title:
                        conversation_id = conversation_data.id
                        break

                if not conversation_id:

                    from src.schemas import ConversationInput

                    conversation_input = ConversationInput(
                        title=f"WhatsApp-{sender_phone}"
                    )

                    new_conversation = await self.conversation_service.create(
                        conversation_input, profile.user_id
                    )

                    conversation_id = new_conversation.data.id

                message_input = MessageInput(content=message_text, context=None)
                await self.conversation_service.add_message(
                    conversation_id=conversation_id,
                    message=message_input,
                    sender=SenderEnum.user,
                    user_id=profile.user_id,
                )

                updated_conversation = await self.conversation_service.find_by_id(
                    conversation_id
                )

                assistant_messages = [
                    msg
                    for msg in updated_conversation.data.messages
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing WhatsApp messages: {str(e)}",
            )
