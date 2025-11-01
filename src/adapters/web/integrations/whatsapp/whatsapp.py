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
                            audio_data = None

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
                            elif msg_type == "audio" and "audio" in msg:
                                # Extract audio message metadata
                                audio = msg.get("audio", {})
                                audio_data = {
                                    "id": audio.get("id"),
                                    "mime_type": audio.get("mime_type", "audio/ogg"),
                                    "sha256": audio.get("sha256"),
                                    "voice": audio.get("voice", False)
                                }
                                logger.info(f"Audio message detected: {audio_data}")

                            message_data = {
                                "from": msg_from,
                                "id": msg_id,
                                "timestamp": msg_timestamp,
                                "type": msg_type,
                                "text": msg_text,
                                "audio": audio_data,
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

    async def download_audio(self, audio_id: str) -> bytes:
        """
        Download audio file from Meta WhatsApp servers
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            media_url = f"https://graph.facebook.com/v18.0/{audio_id}"
            headers = {"Authorization": f"Bearer {self.access_token}"}

            logger.info(f"Fetching audio metadata from: {media_url}")

            response = requests.get(media_url, headers=headers, timeout=30)
            response.raise_for_status()

            media_info = response.json()
            download_url = media_info.get("url")

            if not download_url:
                raise Exception(f"No download URL found in media info: {media_info}")

            logger.info(f"Downloading audio from: {download_url}")

            audio_response = requests.get(download_url, headers=headers, timeout=60)
            audio_response.raise_for_status()

            logger.info(
                f"Successfully downloaded audio: {audio_id}, "
                f"size: {len(audio_response.content)} bytes, "
                f"content-type: {audio_response.headers.get('Content-Type')}"
            )

            return audio_response.content

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error downloading audio {audio_id}: {str(e)}")
            raise Exception(f"Failed to download audio: {str(e)}")
        except Exception as e:
            logger.error(f"Error downloading audio {audio_id}: {str(e)}")
            raise