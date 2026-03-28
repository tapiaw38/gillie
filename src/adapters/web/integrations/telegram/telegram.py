import logging
import requests
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TelegramIntegration:
    def __init__(self, bot_token: str, secret_token: str = "", store_service=None):
        self.bot_token = bot_token
        self.secret_token = secret_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self._store_service = store_service

    def send_message(self, chat_id: str, text: str) -> bool:
        url = f"{self.api_url}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            if result.get("ok"):
                logger.info(f"[telegram] Message sent to {chat_id}")
                return True
            logger.error(f"[telegram] Error sending message: {result}")
            return False
        except Exception as e:
            logger.error(f"[telegram] Exception sending message: {e}", exc_info=True)
            return False

    @staticmethod
    def _is_local_url(url: str) -> bool:
        return "localhost" in url or "127.0.0.1" in url or "0.0.0.0" in url

    def _fetch_bytes(self, url: str) -> Optional[bytes]:
        # For local URLs, read directly from storage to avoid HTTP self-request deadlock
        if self._store_service is not None and self._is_local_url(url):
            try:
                base_url = getattr(self._store_service, "base_url", None)
                if base_url and url.startswith(base_url):
                    key = url[len(base_url):].lstrip("/")
                    return self._store_service.get_object(key)
            except Exception as e:
                logger.error(f"[telegram] Failed to read local file {url}: {e}")
                return None
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            logger.error(f"[telegram] Failed to fetch file from {url}: {e}")
            return None

    def send_image(self, chat_id: str, image_url: str, caption: str = "") -> bool:
        api_url = f"{self.api_url}/sendPhoto"
        try:
            if self._is_local_url(image_url):
                file_bytes = self._fetch_bytes(image_url)
                if not file_bytes:
                    return False
                filename = image_url.split("?")[0].rsplit("/", 1)[-1] or "image.png"
                response = requests.post(
                    api_url,
                    data={"chat_id": chat_id, "caption": caption},
                    files={"photo": (filename, file_bytes)},
                    timeout=30,
                )
            else:
                response = requests.post(api_url, json={"chat_id": chat_id, "photo": image_url, "caption": caption}, timeout=10)
            result = response.json()
            if result.get("ok"):
                logger.info(f"[telegram] Image sent to {chat_id}")
                return True
            logger.error(f"[telegram] Error sending image: {result}")
            return False
        except Exception as e:
            logger.error(f"[telegram] Exception sending image: {e}", exc_info=True)
            return False

    def receive_message(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Telegram Update payload and return list of message dicts."""
        messages = []
        try:
            message = payload.get("message") or payload.get("edited_message")
            if not message:
                return messages

            chat_id = str(message.get("chat", {}).get("id", ""))
            from_user = message.get("from", {})
            user_id = str(from_user.get("id", ""))
            text = message.get("text")
            voice = message.get("voice")
            message_id = str(message.get("message_id", ""))

            # Skip bot messages
            if from_user.get("is_bot"):
                return messages

            if not chat_id or not user_id:
                return messages

            messages.append({
                "chat_id": chat_id,
                "user_id": user_id,
                "text": text,
                "voice": voice,
                "message_id": message_id,
            })
        except Exception as e:
            logger.error(f"[telegram] Error parsing payload: {e}", exc_info=True)
        return messages

    def verify_secret_token(self, header_token: str) -> bool:
        """Verify the X-Telegram-Bot-Api-Secret-Token header."""
        if not self.secret_token:
            return True  # No secret configured — skip verification
        return header_token == self.secret_token

    def download_voice(self, file_id: str) -> Optional[bytes]:
        """Download a voice message file from Telegram servers."""
        try:
            resp = requests.get(
                f"{self.api_url}/getFile",
                params={"file_id": file_id},
                timeout=10,
            )
            file_path = resp.json().get("result", {}).get("file_path")
            if not file_path:
                raise Exception("file_path not found in getFile response")
            token = self.bot_token
            download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
            audio_resp = requests.get(download_url, timeout=60)
            audio_resp.raise_for_status()
            logger.info(f"[telegram] Voice downloaded: {file_id}, size={len(audio_resp.content)}")
            return audio_resp.content
        except Exception as e:
            logger.error(f"[telegram] Error downloading voice {file_id}: {e}", exc_info=True)
            return None

    def send_typing_action(self, chat_id: str) -> None:
        """Send a 'typing' chat action to show the bot is processing."""
        try:
            requests.post(
                f"{self.api_url}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
                timeout=5,
            )
        except Exception as e:
            logger.debug(f"[telegram] Could not send typing action to {chat_id}: {e}")

    def send_document(self, chat_id: str, file_url: str, caption: str = "") -> bool:
        """Send a file/document to a Telegram chat."""
        api_url = f"{self.api_url}/sendDocument"
        filename = file_url.split("?")[0].rsplit("/", 1)[-1] or "file"
        try:
            if self._is_local_url(file_url):
                file_bytes = self._fetch_bytes(file_url)
                if not file_bytes:
                    return False
                response = requests.post(
                    api_url,
                    data={"chat_id": chat_id, "caption": caption},
                    files={"document": (filename, file_bytes)},
                    timeout=30,
                )
            else:
                data: Dict[str, Any] = {"chat_id": chat_id, "document": file_url}
                if caption:
                    data["caption"] = caption
                response = requests.post(api_url, json=data, timeout=15)
            result = response.json()
            if result.get("ok"):
                logger.info(f"[telegram] Document sent to {chat_id}")
                return True
            logger.error(f"[telegram] Error sending document: {result}")
            return False
        except Exception as e:
            logger.error(f"[telegram] Exception sending document: {e}", exc_info=True)
            return False

    def set_webhook(self, webhook_url: str) -> bool:
        """Register the webhook URL with Telegram."""
        data: Dict[str, Any] = {"url": webhook_url}
        if self.secret_token:
            data["secret_token"] = self.secret_token
        try:
            response = requests.post(f"{self.api_url}/setWebhook", json=data, timeout=10)
            result = response.json()
            if result.get("ok"):
                logger.info(f"[telegram] Webhook set to {webhook_url}")
                return True
            logger.error(f"[telegram] Error setting webhook: {result}")
            return False
        except Exception as e:
            logger.error(f"[telegram] Exception setting webhook: {e}", exc_info=True)
            return False
