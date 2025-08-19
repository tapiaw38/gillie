from fastapi import HTTPException, status
from src.schemas.schemas import MessageInput
from src.core.domain.model import SenderEnum, Profile
from src.adapters.web.integrations.whatsapp.whatsapp import WhatsAppIntegration
from src.adapters.services.conversation.service import ConversationService
from typing import Dict, Any, List, Optional

class WhatsAppService:
    def __init__(self, conversation_service: ConversationService):
        self.conversation_service = conversation_service

    async def process_message(self, payload: Dict[Any, Any], profile: Profile):
        """
        Procesa los mensajes entrantes de WhatsApp y responde usando la IA
        """
        # Verificar si la integración de WhatsApp está activada
        import logging
        logger = logging.getLogger(__name__)
        
        whatsapp_integration = None
        
        if profile.integrations:
            for integration in profile.integrations:
                if integration.name == "whatsapp" and integration.activated:
                    whatsapp_integration = integration
                    break
        
        if not whatsapp_integration:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="La integración de WhatsApp no está activada"
            )
            
        # Verificar que la configuración de WhatsApp es válida
        required_configs = ["accessToken", "phoneNumberId"]
        for config in required_configs:
            if config not in whatsapp_integration.config or not whatsapp_integration.config[config]:
                logger.error(f"Configuración de WhatsApp incompleta: falta {config}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"La configuración de WhatsApp no es válida: falta {config}"
                )
        
        try:
            # Inicializar la integración de WhatsApp
            wa_client = WhatsAppIntegration(
                access_token=whatsapp_integration.config["accessToken"],
                phone_number_id=whatsapp_integration.config["phoneNumberId"]
            )
            
            # Procesar mensajes recibidos
            messages = wa_client.receive_message(payload)
            
            if not messages:
                return {"status": "success", "message": "No hay mensajes para procesar"}
            
            responses = []
            
            for msg in messages:
                if msg["type"] != "text" or not msg["text"]:
                    continue
                
                sender_phone = msg["from"]
                message_text = msg["text"]
                message_id = msg["id"]
                
                # Buscar una conversación existente o crear una nueva
                conversation_list = await self.conversation_service.find_by_user_id(profile.user_id)
                
                # Buscar conversación existente con este número de teléfono en el título
                conversation_id = None
                # conversation_list es un objeto ConversationListOutput, necesitamos acceder a data
                for conversation_data in conversation_list.data:
                    if f"WhatsApp-{sender_phone}" in conversation_data.title:
                        conversation_id = conversation_data.id
                        break
                
                if not conversation_id:
                    # Crear una nueva conversación usando el objeto ConversationInput adecuado
                    from src.schemas.schemas import ConversationInput
                    
                    conversation_input = ConversationInput(
                        title=f"WhatsApp-{sender_phone}"
                    )
                    
                    new_conversation = await self.conversation_service.create(
                        conversation_input, 
                        profile.user_id
                    )
                    # El objeto ConversationOutput tiene una estructura anidada, el ID está en data.id
                    conversation_id = new_conversation.data.id
                
                # Agregar el mensaje recibido a la conversación
                message_input = MessageInput(content=message_text, context=None)
                await self.conversation_service.add_message(
                    conversation_id=conversation_id,
                    message=message_input,
                    sender=SenderEnum.user,
                    user_id=profile.user_id
                )
                
                # La respuesta ya será generada automáticamente por el caso de uso add_message
                # que debe invocar a la IA y generar una respuesta como assistant
                
                # Obtener la conversación actualizada con la respuesta de la IA
                updated_conversation = await self.conversation_service.find_by_id(conversation_id)
                
                # Obtener la última respuesta de la IA
                # El objeto ConversationOutput tiene una estructura anidada, los mensajes están en data.messages
                import logging
                logger = logging.getLogger(__name__)
                
                assistant_messages = [msg for msg in updated_conversation.data.messages if msg.sender == SenderEnum.assistant]
                if assistant_messages:
                    last_assistant_message = assistant_messages[-1]
                    
                    logger.info(f"Enviando respuesta de IA a WhatsApp: teléfono={sender_phone}, mensaje_id={message_id}")
                    
                    # Enviar la respuesta de vuelta a WhatsApp
                    sent = wa_client.send_message(sender_phone, last_assistant_message.content)
                    
                    if sent:
                        logger.info(f"Respuesta enviada correctamente a WhatsApp: teléfono={sender_phone}")
                    else:
                        logger.warning(f"Falló el envío de la respuesta a WhatsApp: teléfono={sender_phone}")
                    
                    responses.append({
                        "phone": sender_phone,
                        "message_id": message_id,
                        "response_sent": sent,
                        "message": last_assistant_message.content[:100] + "..." if len(last_assistant_message.content) > 100 else last_assistant_message.content
                    })
                else:
                    logger.warning(f"No se encontraron mensajes del asistente para enviar como respuesta: conversation_id={conversation_id}")
                
            return {"status": "success", "processed_messages": responses}
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al procesar mensajes de WhatsApp: {str(e)}"
            )
