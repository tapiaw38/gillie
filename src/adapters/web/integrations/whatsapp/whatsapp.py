import requests

class WhatsAppIntegration:
    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"

    def send_message(self, recipient: str, message: str) -> bool:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message}
        }
        response = requests.post(self.api_url, headers=headers, json=data)
        return response.status_code == 200

    def receive_message(self, payload):
        """
        Extrae mensajes de la carga útil del webhook de WhatsApp
        Maneja diferentes formatos y estructura de mensajes para mayor compatibilidad
        """
        import logging
        logger = logging.getLogger(__name__)
        
        messages = []
        try:
            # Log detallado de la estructura para depuración
            logger.debug(f"Analizando payload para extraer mensajes: {payload}")
            
            # Método principal para extraer mensajes de la estructura estándar
            if "entry" in payload:
                entry = payload.get("entry", [])
                for ent in entry:
                    changes = ent.get("changes", [])
                    for change in changes:
                        value = change.get("value", {})
                        
                        # Log del valor para depuración
                        logger.debug(f"Analizando value para mensajes: {value}")
                        
                        messages_list = value.get("messages", [])
                        for msg in messages_list:
                            # Extraer campos relevantes
                            msg_from = msg.get("from")
                            msg_id = msg.get("id")
                            msg_timestamp = msg.get("timestamp")
                            msg_type = msg.get("type")
                            
                            # Extraer el texto según el tipo de mensaje
                            msg_text = None
                            if msg_type == "text" and "text" in msg:
                                msg_text = msg.get("text", {}).get("body")
                            elif msg_type == "button" and "button" in msg:
                                msg_text = msg.get("button", {}).get("text")
                            elif msg_type == "interactive" and "interactive" in msg:
                                interactive_data = msg.get("interactive", {})
                                if "button_reply" in interactive_data:
                                    msg_text = interactive_data.get("button_reply", {}).get("title")
                                elif "list_reply" in interactive_data:
                                    msg_text = interactive_data.get("list_reply", {}).get("title")
                            
                            # Crear estructura del mensaje
                            message_data = {
                                "from": msg_from,
                                "id": msg_id,
                                "timestamp": msg_timestamp,
                                "type": msg_type,
                                "text": msg_text,
                                "raw": msg
                            }
                            
                            # Solo agregar mensajes que tengan remitente e ID
                            if msg_from and msg_id:
                                messages.append(message_data)
                                logger.debug(f"Mensaje extraído: {message_data}")
            
            # Método alternativo para mensajes en formato diferente
            if not messages and "messages" in payload:
                direct_messages = payload.get("messages", [])
                for msg in direct_messages:
                    # Extraer campos relevantes
                    msg_from = msg.get("from")
                    msg_id = msg.get("id")
                    msg_type = msg.get("type")
                    msg_text = None
                    
                    # Extraer texto según tipo
                    if msg_type == "text":
                        msg_text = msg.get("text", {}).get("body") if "text" in msg else msg.get("body")
                    
                    message_data = {
                        "from": msg_from,
                        "id": msg_id,
                        "timestamp": msg.get("timestamp"),
                        "type": msg_type,
                        "text": msg_text,
                        "raw": msg
                    }
                    
                    if msg_from and msg_id:
                        messages.append(message_data)
                        logger.debug(f"Mensaje extraído (formato alternativo): {message_data}")
            
            # Registrar número de mensajes encontrados
            logger.info(f"Total de mensajes extraídos del payload: {len(messages)}")
            
        except Exception as e:
            logger.error(f"Error al procesar el payload de WhatsApp: {str(e)}", exc_info=True)
            # No lanzar excepción, solo registrar el error y devolver lista vacía
        
        return messages