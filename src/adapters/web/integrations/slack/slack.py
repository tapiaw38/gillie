import hashlib
import hmac
import logging
import time
from typing import List, Dict, Any

import requests


class SlackIntegration:
    """
    Adapter for the Slack Web API and Events API.

    Handles outbound message delivery and inbound event parsing.
    Signature verification follows Slack's official HMAC-SHA256 scheme.
    """

    def __init__(self, bot_token: str, signing_secret: str = ""):
        self.bot_token = bot_token
        self.signing_secret = signing_secret
        self.api_url = "https://slack.com/api"

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }

    def auth_test(self) -> Dict[str, Any]:
        """
        Validate the bot token and return workspace/app metadata.
        """
        url = f"{self.api_url}/auth.test"
        response = requests.post(url, headers=self._build_headers(), timeout=10)
        response.raise_for_status()
        result = response.json() if response.content else {}
        if not result.get("ok"):
            raise ValueError(f"Slack auth.test failed: {result.get('error', 'unknown_error')}")
        return result

    def send_message(self, channel: str, text: str) -> bool:
        """
        Post a plain-text message to a Slack channel.

        Returns True when Slack acknowledges the delivery (ok=true).
        """
        logger = logging.getLogger(__name__)

        url = f"{self.api_url}/chat.postMessage"
        payload = {"channel": channel, "text": text}

        try:
            response = requests.post(url, headers=self._build_headers(), json=payload, timeout=10)
            response_json = response.json() if response.content else {}

            if response_json.get("ok"):
                logger.info(f"Slack message sent successfully to channel={channel}")
                return True

            logger.error(
                f"Slack send_message error: channel={channel}, "
                f"error={response_json.get('error')}, response={response_json}"
            )
            return False

        except Exception as e:
            logger.error(f"Exception while sending Slack message: {str(e)}", exc_info=True)
            return False

    def send_image(self, channel: str, image_url: str, caption: str = "") -> bool:
        """
        Post an image block to a Slack channel.

        Uses Slack's Block Kit image element so the image renders inline.
        Returns True when Slack acknowledges the delivery (ok=true).
        """
        logger = logging.getLogger(__name__)

        url = f"{self.api_url}/chat.postMessage"
        payload = {
            "channel": channel,
            "text": caption,
            "blocks": [
                {
                    "type": "image",
                    "image_url": image_url,
                    "alt_text": caption or "image",
                }
            ],
        }

        try:
            response = requests.post(url, headers=self._build_headers(), json=payload, timeout=10)
            response_json = response.json() if response.content else {}

            if response_json.get("ok"):
                logger.info(f"Slack image sent successfully to channel={channel}")
                return True

            logger.error(
                f"Slack send_image error: channel={channel}, "
                f"error={response_json.get('error')}, response={response_json}"
            )
            return False

        except Exception as e:
            logger.error(f"Exception while sending Slack image: {str(e)}", exc_info=True)
            return False

    def send_document(self, channel: str, file_url: str, caption: str = "", filename: str = "") -> bool:
        """
        Share a document/file in a Slack channel by posting its URL as a message.
        Uses a simple text+snippet block so the file is accessible via link.
        """
        if not filename:
            filename = file_url.split("?")[0].rsplit("/", 1)[-1] or "file"
        text = f"{caption}\n{file_url}".strip() if caption else file_url
        url = f"{self.api_url}/chat.postMessage"
        payload = {"channel": channel, "text": text}
        try:
            response = requests.post(url, headers=self._build_headers(), json=payload, timeout=10)
            result = response.json() if response.content else {}
            if result.get("ok"):
                logger.info(f"Slack document sent to channel={channel}: {filename}")
                return True
            logger.error(f"Slack send_document error: channel={channel}, error={result.get('error')}")
            return False
        except Exception as e:
            logger.error(f"Exception while sending Slack document: {e}", exc_info=True)
            return False

    def receive_message(self, payload: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Parse a Slack Events API payload and return a list of user messages.

        Only processes event_callback payloads of type "message".
        Bot messages (bot_id present) and message subtypes (edits, deletions)
        are silently skipped to avoid echo loops and noise.

        Returns a list of dicts with keys: user_id, channel, text, ts.
        """
        logger = logging.getLogger(__name__)
        messages: List[Dict[str, str]] = []

        try:
            if payload.get("type") != "event_callback":
                logger.debug(f"Skipping non-event_callback payload type: {payload.get('type')}")
                return messages

            event = payload.get("event", {})

            if event.get("type") != "message":
                logger.debug(f"Skipping non-message event type: {event.get('type')}")
                return messages

            # Skip bot messages to prevent echo loops
            if "bot_id" in event:
                logger.debug("Skipping bot message")
                return messages

            # Skip message subtypes such as message_changed or message_deleted
            if event.get("subtype"):
                logger.debug(f"Skipping message with subtype: {event.get('subtype')}")
                return messages

            user_id = event.get("user")
            channel = event.get("channel")
            text = event.get("text", "")
            ts = event.get("ts", "")

            if not user_id or not channel or not text:
                logger.warning(
                    f"Incomplete message event: user_id={user_id}, channel={channel}, text={text!r}"
                )
                return messages

            messages.append({"user_id": user_id, "channel": channel, "text": text, "ts": ts})
            logger.debug(f"Extracted Slack message: user_id={user_id}, channel={channel}")

        except Exception as e:
            logger.error(f"Error processing Slack payload: {str(e)}", exc_info=True)

        return messages

    def verify_signature(self, raw_body: bytes, timestamp: str, signature: str) -> bool:
        """
        Verify a Slack request signature using HMAC-SHA256 and a 5-minute replay window.
        """
        if not self.signing_secret or not timestamp or not signature:
            return False

        try:
            request_ts = int(timestamp)
        except (TypeError, ValueError):
            return False

        if abs(time.time() - request_ts) > 60 * 5:
            return False

        base = f"v0:{timestamp}:{raw_body.decode('utf-8')}"
        computed = "v0=" + hmac.new(
            self.signing_secret.encode("utf-8"),
            base.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed, signature)
