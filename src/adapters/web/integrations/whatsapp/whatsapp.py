import requests


class WhatsAppIntegration:
    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_url = (
            f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        )

    def send_message(self, recipient: str, message: str) -> bool:
        import logging

        logger = logging.getLogger(__name__)

        recipient = "".join(filter(str.isdigit, recipient))

        logger.info(
            f"Sending message to WhatsApp: url={self.api_url}, recipient={recipient}"
        )

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        data = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message},
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response_json = response.json() if response.content else {}

            if response.status_code == 200:
                logger.info(
                    f"Message sent successfully: {response.status_code} {response.reason}"
                )
                return True
            else:
                logger.error(
                    f"Error sending message: status={response.status_code}, response={response_json}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Exception while sending WhatsApp message: {str(e)}", exc_info=True
            )
            return False

    def receive_message(self, payload):
        import logging

        logger = logging.getLogger(__name__)

        messages = []
        try:
            logger.debug(f"Analyzed payload: {payload}")

            if "entry" in payload:
                entry = payload.get("entry", [])
                for ent in entry:
                    changes = ent.get("changes", [])
                    for change in changes:
                        value = change.get("value", {})

                        messages_list = value.get("messages", [])
                        for msg in messages_list:
                            msg_from = msg.get("from")
                            msg_id = msg.get("id")
                            msg_timestamp = msg.get("timestamp")
                            msg_type = msg.get("type")

                            msg_text = None
                            if msg_type == "text" and "text" in msg:
                                msg_text = msg.get("text", {}).get("body")
                            elif msg_type == "button" and "button" in msg:
                                msg_text = msg.get("button", {}).get("text")
                            elif msg_type == "interactive" and "interactive" in msg:
                                interactive_data = msg.get("interactive", {})
                                if "button_reply" in interactive_data:
                                    msg_text = interactive_data.get(
                                        "button_reply", {}
                                    ).get("title")
                                elif "list_reply" in interactive_data:
                                    msg_text = interactive_data.get(
                                        "list_reply", {}
                                    ).get("title")

                            message_data = {
                                "from": msg_from,
                                "id": msg_id,
                                "timestamp": msg_timestamp,
                                "type": msg_type,
                                "text": msg_text,
                                "raw": msg,
                            }

                            if msg_from and msg_id:
                                messages.append(message_data)
                                logger.debug(f"Extracted message: {message_data}")

            if not messages and "messages" in payload:
                direct_messages = payload.get("messages", [])
                for msg in direct_messages:
                    msg_from = msg.get("from")
                    msg_id = msg.get("id")
                    msg_type = msg.get("type")
                    msg_text = None

                    if msg_type == "text":
                        msg_text = (
                            msg.get("text", {}).get("body")
                            if "text" in msg
                            else msg.get("body")
                        )

                    message_data = {
                        "from": msg_from,
                        "id": msg_id,
                        "timestamp": msg.get("timestamp"),
                        "type": msg_type,
                        "text": msg_text,
                        "raw": msg,
                    }

                    if msg_from and msg_id:
                        messages.append(message_data)
                        logger.debug(
                            f"Extracted message (alternative format): {message_data}"
                        )

            logger.info(f"Total messages extracted from payload: {len(messages)}")

        except Exception as e:
            logger.error(
                f"Error processing WhatsApp payload: {str(e)}", exc_info=True
            )

        return messages