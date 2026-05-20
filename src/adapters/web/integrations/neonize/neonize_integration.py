"""
NeonizeIntegration — Python WhatsApp client pool using neonize (whatsmeow bindings).

Each device_id maps to a persistent neonize client backed by a SQLite session file.
Sessions are stored at: {sessions_dir}/{device_id}.db

Key neonize internals (from source inspection):
- neonize uses its OWN global asyncio event loop (`event_global_loop`) separate from uvicorn's.
- Events are dispatched via `asyncio.run_coroutine_threadsafe(handler, event_global_loop)`.
- That loop MUST be running (in a daemon thread) or events are silently dropped.
- All @client.event handlers receive TWO args: (client, event), NOT just (event).
- client.connect() is async but returns immediately (creates a task on event_global_loop).
"""
import asyncio
import base64
import io
import logging
import os
import threading
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

_neonize_loop_started = False
_neonize_loop: Optional[asyncio.AbstractEventLoop] = None


def _prefer_contact_jid(candidates: list[str]) -> str:
    for candidate in candidates:
        if candidate and not candidate.endswith("@lid"):
            return candidate
    for candidate in candidates:
        if candidate:
            return candidate
    return ""


def _select_reply_jid(sender: str, resolved: str) -> str:
    if sender:
        return sender
    return resolved


def _ensure_neonize_loop() -> None:
    """
    Create a new asyncio event loop, register it with neonize via set_event_loop(),
    and start it in a background daemon thread.

    neonize >= 0.3.16 changed the API: event_global_loop starts as None and must be
    set explicitly (or is set automatically when connect() runs inside a running loop).
    We pre-create and register the loop here so Go callbacks can dispatch events even
    before connect() is awaited.
    """
    global _neonize_loop_started, _neonize_loop
    if _neonize_loop_started:
        return
    try:
        from neonize.aioze.events import set_event_loop
        _neonize_loop = asyncio.new_event_loop()
        set_event_loop(_neonize_loop)
        thread = threading.Thread(target=_neonize_loop.run_forever, daemon=True)
        thread.start()
        logger.info("[neonize] event_global_loop created and started in background daemon thread")
        _neonize_loop_started = True
    except ImportError:
        pass  # neonize not installed — will fail later with a clear error


class NeonizeIntegration:
    """
    Manages a pool of neonize WhatsApp clients, one per device.

    Usage:
        integration = NeonizeIntegration(sessions_dir="./data/whatsapp")
        await integration.start_qr_auth(device_id, on_qr_ready, on_authenticated)
        await integration.send_text(device_id, jid, "Hello!")
        await integration.disconnect(device_id)
    """

    def __init__(self, sessions_dir: str = "./data/whatsapp", stt_integration=None, whatsapp_device_repository=None, profile_repository=None):
        self.sessions_dir = sessions_dir
        os.makedirs(sessions_dir, exist_ok=True)
        self._clients: Dict[str, object] = {}  # device_id → NewAClient
        self._app_loop: Optional[asyncio.AbstractEventLoop] = None
        self._stt_integration = stt_integration  # optional STT for audio transcription
        self._whatsapp_device_repository = whatsapp_device_repository
        self._profile_repository = profile_repository
        # Per-device+JID queues and workers ensure messages from the same sender
        # are always processed in order without dropping concurrent messages.
        self._jid_queues: Dict[str, asyncio.Queue] = {}   # key: "{device_id}:{jid}"
        self._jid_workers: Dict[str, asyncio.Task] = {}   # key: "{device_id}:{jid}"
        _ensure_neonize_loop()

    def set_app_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._app_loop = loop

    def _session_path(self, device_id: str) -> str:
        return os.path.join(self.sessions_dir, f"{device_id}.db")

    _LANG_MAP = {"en": "en-US", "es": "es-ES", "fr": "fr-FR", "de": "de-DE", "pt": "pt-BR", "it": "it-IT"}

    async def _get_stt_language(self, device_id: str) -> str:
        """Resolve the STT language from the device owner's profile response_language."""
        try:
            if self._whatsapp_device_repository and self._profile_repository:
                device = await self._whatsapp_device_repository.find_by_id(device_id)
                if device:
                    profile = await self._profile_repository.find_by_user_id(device.user_id)
                    if profile:
                        lang = getattr(profile, "response_language", None) or "en"
                        return self._LANG_MAP.get(lang, f"{lang}-{lang.upper()}")
        except Exception:
            pass
        return "es-ES"

    async def create_client(self, device_id: str) -> object:
        """Create (or return existing) neonize client for device_id."""
        if device_id in self._clients:
            return self._clients[device_id]

        try:
            from neonize.aioze.client import NewAClient
        except ImportError as e:
            raise RuntimeError(
                "neonize is not installed. Run: pip install neonize"
            ) from e

        session_path = self._session_path(device_id)
        client = NewAClient(session_path)
        self._clients[device_id] = client
        logger.info(f"[neonize] Created client for device {device_id} at {session_path}")
        return client

    async def get_client(self, device_id: str) -> object:
        if device_id not in self._clients:
            raise ValueError(f"No client for device {device_id}. Call create_client first.")
        return self._clients[device_id]

    async def start_qr_auth(
        self,
        device_id: str,
        on_qr_ready: Callable,                    # async fn(qr_data_url: str) -> None
        on_authenticated: Callable,               # async fn() -> None
        message_handler: Optional[Callable] = None,  # async fn(device_id, sender_jid, text) -> None
    ) -> None:
        """
        Start QR authentication without blocking.

        Registers ALL event handlers (QR, PairStatus, MessageEv) before the single
        client.connect() call, so Go's event-dispatch list (d) includes MessageEv from
        the start. This avoids the double-connect/StreamReplaced race condition.

        Neonize QR architecture:
        - QR arrives via client.__onQr → event._qr(client, bytes), NOT via @client.event(QREv).
        - client.connect() must run on event_global_loop (thread-safe create_task).
        """
        try:
            import qrcode
        except ImportError as e:
            raise RuntimeError(
                "neonize and/or qrcode[pil] are not installed."
            ) from e

        _ensure_neonize_loop()
        client = await self.create_client(device_id)

        # Primary QR callback — neonize calls event._qr(client, bytes) from Go thread
        async def _on_qr(_client, qr_bytes: bytes) -> None:
            logger.info(f"[neonize] QR received for device {device_id}")
            try:
                qr_string = qr_bytes.decode() if isinstance(qr_bytes, bytes) else str(qr_bytes)
                img = qrcode.make(qr_string)
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                b64 = base64.b64encode(buffer.getvalue()).decode()
                await on_qr_ready(f"data:image/png;base64,{b64}")
                logger.info(f"[neonize] QR stored in DB for device {device_id}")
            except Exception as exc:
                logger.error(f"[neonize] _on_qr error for device {device_id}: {exc}", exc_info=True)

        client.qr(_on_qr)

        try:
            from neonize.aioze.events import PairStatusEv

            @client.event(PairStatusEv)
            async def on_pair_status(_client, event):
                logger.info(f"[neonize] PairStatusEv fired for device {device_id}")
                try:
                    await on_authenticated()
                except Exception as exc:
                    logger.error(
                        f"[neonize] on_authenticated error for device {device_id}: {exc}",
                        exc_info=True,
                    )
        except (ImportError, AttributeError):
            logger.warning("[neonize] PairStatusEv not available — auth won't be auto-detected")

        if message_handler is not None:
            try:
                from neonize.aioze.events import MessageEv

                @client.event(MessageEv)
                async def on_message(_client, msg_event):
                    print(f"[neonize] MessageEv received for device {device_id}", flush=True)
                    logger.info(f"[neonize] MessageEv received for device {device_id}")
                    try:
                        await self._dispatch_message(device_id, msg_event, message_handler)
                    except Exception as exc:
                        logger.error(
                            f"[neonize] on_message error for device {device_id}: {exc}",
                            exc_info=True,
                        )
            except (ImportError, AttributeError):
                logger.warning("[neonize] MessageEv not available")

        logger.info(
            f"[neonize] Connecting device {device_id} with event codes: "
            f"{list(client.event.list_func.keys())}"
        )

        def _on_connect_done(future):
            exc = future.exception()
            if exc:
                logger.error(f"[neonize] connect() failed for device {device_id}: {exc}", exc_info=exc)

        fut = asyncio.run_coroutine_threadsafe(client.connect(), _neonize_loop)
        fut.add_done_callback(_on_connect_done)
        logger.info(f"[neonize] Started QR auth for device {device_id}")

    async def get_pair_code(self, device_id: str, phone_number: str) -> str:
        """Request a pair code for the given phone number."""
        _ensure_neonize_loop()
        client = await self.create_client(device_id)

        if not self._is_running(device_id):
            asyncio.run_coroutine_threadsafe(client.connect(), _neonize_loop)
            await asyncio.sleep(2)

        try:
            pair_code = await client.pair_phone(phone_number)
            return pair_code
        except Exception as e:
            logger.error(f"[neonize] pair_phone failed for device {device_id}: {e}", exc_info=True)
            raise

    async def connect(self, device_id: str, message_handler: Optional[Callable] = None) -> None:
        """
        Connect the client and optionally register a message handler.
        The message_handler receives (device_id, sender_jid, text).

        If the client is already running (e.g. after start_qr_auth registered MessageEv
        and connected), this is a no-op to avoid StreamReplaced races.
        """
        _ensure_neonize_loop()

        if self._is_running(device_id):
            logger.info(
                f"[neonize] Device {device_id} already connected — skipping reconnect"
            )
            return

        client = await self.create_client(device_id)

        try:
            from neonize.aioze.events import ConnectedEv, MessageEv
        except ImportError as e:
            raise RuntimeError("neonize is not installed.") from e

        @client.event(ConnectedEv)
        async def on_connected(_client, _event):
            print(f"[neonize] ConnectedEv fired for device {device_id}", flush=True)
            logger.info(f"[neonize] ConnectedEv fired for device {device_id} — event dispatch working")

        if message_handler is not None:
            @client.event(MessageEv)
            async def on_message(_client, msg_event):
                print(f"[neonize] MessageEv received for device {device_id}", flush=True)
                logger.info(f"[neonize] MessageEv received for device {device_id}")
                try:
                    await self._dispatch_message(device_id, msg_event, message_handler)
                except Exception as exc:
                    logger.error(
                        f"[neonize] Error handling message for device {device_id}: {exc}",
                        exc_info=True,
                    )

        logger.info(
            f"[neonize] Connecting device {device_id} with event codes: "
            f"{list(client.event.list_func.keys())}"
        )

        def _on_connect_done(future):
            exc = future.exception()
            if exc:
                logger.error(f"[neonize] connect() failed for device {device_id}: {exc}", exc_info=exc)

        fut = asyncio.run_coroutine_threadsafe(client.connect(), _neonize_loop)
        fut.add_done_callback(_on_connect_done)
        logger.info(f"[neonize] Device {device_id} connected and listening")

    async def disconnect(self, device_id: str) -> None:
        """Disconnect and remove the client from the pool."""
        if device_id not in self._clients:
            return
        client = self._clients[device_id]
        try:
            await client.disconnect()
        except Exception as e:
            logger.warning(f"[neonize] Error disconnecting device {device_id}: {e}")
        finally:
            self._clients.pop(device_id, None)
            logger.info(f"[neonize] Device {device_id} disconnected")

    async def remove_client(self, device_id: str) -> None:
        """Disconnect client and delete its session file from disk."""
        await self.disconnect(device_id)
        session_path = self._session_path(device_id)
        if os.path.exists(session_path):
            os.remove(session_path)
            logger.info(f"[neonize] Session file deleted: {session_path}")

    async def send_text(self, device_id: str, jid: str, text: str) -> str:
        """Send a text message to the given JID. Returns the message ID.

        jid must be a "user@server" string (e.g. "5491112345678@s.whatsapp.net").
        neonize's send_message requires a JID protobuf object, so we build it here.

        Retries up to 3 times with exponential backoff on transient SendMessageError
        (e.g. "failed to get device list: failed to send usync query").
        """
        from neonize.utils.jid import build_jid
        from neonize.exc import SendMessageError

        if "@" in jid:
            user, server = jid.rsplit("@", 1)
        else:
            user, server = jid, "s.whatsapp.net"
        jid_proto = build_jid(user, server)

        client = await self.get_client(device_id)

        # Send composing presence indicator before the message
        try:
            from neonize.proto.Neonize_pb2 import ChatPresence, ChatPresenceMedia
            await client.send_chat_presence(
                jid_proto,
                ChatPresence.CHAT_PRESENCE_COMPOSING,
                ChatPresenceMedia.CHAT_PRESENCE_MEDIA_TEXT,
            )
        except Exception as _pe:
            logger.debug(f"[neonize] Could not send composing presence for {jid}: {_pe}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await client.send_message(jid_proto, text)
                msg_id = str(result.id) if hasattr(result, "id") else str(result)
                logger.info(f"[neonize] Sent message to {jid} via device {device_id}: id={msg_id}")
                return msg_id
            except SendMessageError as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt  # 1s, 2s, ...
                    logger.warning(
                        f"[neonize] send_message attempt {attempt + 1}/{max_retries} failed for "
                        f"{jid} via device {device_id}: {e} — retrying in {wait}s"
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        f"[neonize] Failed to send message to {jid} via device {device_id} "
                        f"after {max_retries} attempts: {e}",
                        exc_info=True,
                    )
                    raise
            except Exception as e:
                logger.error(
                    f"[neonize] Failed to send message to {jid} via device {device_id}: {e}",
                    exc_info=True,
                )
                raise

    async def send_image(self, device_id: str, jid: str, image_url: str, caption: str = "") -> Optional[str]:
        """Download an image from image_url and send it to the given JID."""
        import aiohttp
        from neonize.utils.jid import build_jid

        if "@" in jid:
            user, server = jid.rsplit("@", 1)
        else:
            user, server = jid, "s.whatsapp.net"
        jid_proto = build_jid(user, server)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    resp.raise_for_status()
                    image_bytes = await resp.read()

            client = await self.get_client(device_id)
            result = await client.send_image(jid_proto, image_bytes, caption=caption)
            msg_id = str(result.id) if hasattr(result, "id") else str(result)
            logger.info(f"[neonize] Sent image to {jid} via device {device_id}: id={msg_id}")
            return msg_id

        except Exception as e:
            logger.error(
                f"[neonize] Failed to send image to {jid} via device {device_id}: {e}",
                exc_info=True,
            )
            return None

    async def send_document(self, device_id: str, jid: str, file_url: str, caption: str = "", filename: str = "") -> Optional[str]:
        """Download a file from file_url and send it as a document to the given JID."""
        import aiohttp
        import mimetypes
        from neonize.utils.jid import build_jid

        if "@" in jid:
            user, server = jid.rsplit("@", 1)
        else:
            user, server = jid, "s.whatsapp.net"
        jid_proto = build_jid(user, server)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    resp.raise_for_status()
                    file_bytes = await resp.read()
                    content_type = resp.headers.get("Content-Type", "application/octet-stream").split(";")[0]

            if not filename:
                filename = file_url.split("?")[0].rsplit("/", 1)[-1] or "file"

            mime = content_type or (mimetypes.guess_type(filename)[0] or "application/octet-stream")

            client = await self.get_client(device_id)
            result = await client.send_document(jid_proto, file_bytes, caption=caption, filename=filename, mimetype=mime)
            msg_id = str(result.id) if hasattr(result, "id") else str(result)
            logger.info(f"[neonize] Sent document '{filename}' to {jid} via device {device_id}: id={msg_id}")
            return msg_id

        except Exception as e:
            logger.error(f"[neonize] Failed to send document to {jid} via device {device_id}: {e}", exc_info=True)
            return None

    async def send_audio(self, device_id: str, jid: str, audio_url: str) -> Optional[str]:
        import subprocess
        import tempfile
        import aiohttp
        from neonize.utils.jid import build_jid

        if "@" in jid:
            user, server = jid.rsplit("@", 1)
        else:
            user, server = jid, "s.whatsapp.net"
        jid_proto = build_jid(user, server)

        tmp_src = None
        tmp_ogg = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as resp:
                    resp.raise_for_status()
                    src_bytes = await resp.read()

            logger.info(
                "[neonize] Downloaded audio %d bytes from %s for device %s",
                len(src_bytes), audio_url[:60], device_id,
            )

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(src_bytes)
                tmp_src = f.name

            tmp_ogg = tmp_src.replace(".wav", ".ogg")
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", tmp_src,
                "-vn",
                "-acodec", "libopus",
                "-b:a", "64k",
                "-ar", "48000",
                "-ac", "1",
                tmp_ogg,
            ]
            conv = subprocess.run(ffmpeg_cmd, capture_output=True, timeout=30)
            if conv.returncode != 0:
                logger.error("[neonize] ffmpeg WAV→OGG failed: %s", conv.stderr[-300:])
                return None

            with open(tmp_ogg, "rb") as f:
                audio_bytes = f.read()
            logger.info("[neonize] Converted to OGG Opus: %d bytes", len(audio_bytes))

            from io import BytesIO
            from neonize.aioze.client import AFFmpeg, AudioMessage, MediaType, Message

            client = await self.get_client(device_id)
            upload = await client.upload(audio_bytes, MediaType.MediaAudio)

            async with AFFmpeg(audio_bytes) as ffmpeg:
                duration = int((await ffmpeg.extract_info()).format.duration)

            message = Message(
                audioMessage=AudioMessage(
                    URL=upload.url,
                    directPath=upload.DirectPath,
                    fileEncSHA256=upload.FileEncSHA256,
                    fileLength=upload.FileLength,
                    fileSHA256=upload.FileSHA256,
                    mediaKey=upload.MediaKey,
                    mimetype="audio/ogg; codecs=opus",
                    seconds=duration,
                    PTT=False,
                )
            )
            result = await client.send_message(jid_proto, message)
            msg_id = str(result.id) if hasattr(result, "id") else str(result)
            logger.info(
                "[neonize] Sent audio to %s via device %s: id=%s",
                jid, device_id, msg_id,
            )
            return msg_id

        except Exception as e:
            logger.error(
                "[neonize] Failed to send audio to %s via device %s: %s",
                jid, device_id, e,
                exc_info=True,
            )
            return None
        finally:
            for path in (tmp_src, tmp_ogg):
                if path and os.path.exists(path):
                    os.unlink(path)

    def _is_running(self, device_id: str) -> bool:
        return device_id in self._clients

    async def _transcribe_audio(self, device_id: str, msg_event, audio_msg) -> str:
        """Download a WhatsApp audio message and transcribe it via STT.

        Returns the transcribed text, or empty string if STT is unavailable or fails.
        """
        if self._stt_integration is None:
            logger.debug("[neonize] STT not configured — skipping audio transcription")
            return ""

        try:
            client = await self.get_client(device_id)
            wa_msg = getattr(msg_event, "Message", None)
            if wa_msg is None:
                return ""
            audio_bytes = await client.download_any(wa_msg)
            if not audio_bytes:
                logger.warning(f"[neonize] download_any returned empty for device {device_id}")
                return ""

            mimetype = getattr(audio_msg, "mimetype", "audio/ogg")
            if "ogg" in mimetype:
                audio_format = "ogg"
            elif "mp4" in mimetype or "m4a" in mimetype or "aac" in mimetype:
                audio_format = "mp4"
            elif "mp3" in mimetype or "mpeg" in mimetype:
                audio_format = "mp3"
            else:
                audio_format = "ogg"

            duration = getattr(audio_msg, "seconds", 0)
            logger.info(
                f"[neonize] Transcribing audio ({duration}s, {audio_format}) for device {device_id}"
            )

            stt_language = await self._get_stt_language(device_id)
            logger.info(f"[neonize] STT language for device {device_id}: {stt_language}")
            result = await self._stt_integration.audio_bytes_to_text(
                audio_bytes=audio_bytes,
                audio_format=audio_format,
                settings={"language": stt_language},
            )

            if result.get("success") and result.get("text"):
                text = result["text"]
                logger.info(f"[neonize] Audio transcribed for device {device_id}: {text[:80]!r}")
                return text

            logger.warning(
                f"[neonize] STT failed for device {device_id}: {result.get('error', 'unknown')}"
            )
            return ""

        except Exception as e:
            logger.error(f"[neonize] Audio transcription error for device {device_id}: {e}", exc_info=True)
            return ""

    async def _dispatch_message(
        self,
        device_id: str,
        msg_event,
        handler: Callable,
    ) -> None:
        """Extract sender JID and text from a MessageEv and enqueue it for processing.

        Messages from the same sender (device+JID) are enqueued so they are
        always processed sequentially, preventing race conditions when the user
        sends multiple messages before the AI finishes responding.

        Neonize protobuf uses PascalCase field names:
          msg_event.Info             → MessageInfo
          msg_event.Info.MessageSource.IsFromMe → bool
          msg_event.Info.MessageSource.Sender   → JID
          msg_event.Message          → waE2E.Message (uses camelCase: conversation, extendedTextMessage)
        """
        try:
            info = getattr(msg_event, "Info", None)
            if info is None:
                logger.debug(f"[neonize] _dispatch_message: no Info field, skipping")
                return

            src = getattr(info, "MessageSource", None)
            if src is None:
                logger.debug(f"[neonize] _dispatch_message: no MessageSource, skipping")
                return

            if getattr(src, "IsFromMe", False):
                return

            from neonize.utils.jid import Jid2String
            sender_obj = getattr(src, "Sender", None)
            sender_alt_obj = getattr(src, "SenderAlt", None)
            chat_obj = getattr(src, "Chat", None)
            raw_sender_alt = Jid2String(sender_alt_obj) if sender_alt_obj is not None else ""
            raw_sender = Jid2String(sender_obj) if sender_obj is not None else ""
            raw_chat = Jid2String(chat_obj) if chat_obj is not None else ""
            sender_candidates = [raw_sender_alt, raw_sender, raw_chat]
            sender_jid = _prefer_contact_jid(sender_candidates)
            reply_jid = _select_reply_jid(raw_sender, sender_jid)
            if not sender_jid:
                return

            wa_msg = getattr(msg_event, "Message", None)
            text = ""
            if wa_msg is not None:
                text = (
                    getattr(wa_msg, "conversation", "")
                    or getattr(getattr(wa_msg, "extendedTextMessage", None), "text", "")
                )

                if not text:
                    audio_msg = getattr(wa_msg, "audioMessage", None)
                    if audio_msg and getattr(audio_msg, "seconds", 0) > 0:
                        text = await self._transcribe_audio(device_id, msg_event, audio_msg)

            if not text:
                logger.debug(
                    f"[neonize] _dispatch_message: no text in message from {sender_jid}, skipping"
                )
                return

            logger.info(
                f"[neonize] Queuing message from {sender_jid} on device {device_id}: {text[:50]!r}"
            )
            await self._enqueue_message(
                device_id,
                sender_jid,
                reply_jid,
                sender_candidates,
                text,
                handler,
            )

        except Exception as e:
            logger.error(f"[neonize] _dispatch_message error: {e}", exc_info=True)

    async def _enqueue_message(
        self,
        device_id: str,
        sender_jid: str,
        reply_jid: str,
        sender_candidates: list[str],
        text: str,
        handler: Callable,
    ) -> None:
        """Put a message in the per-JID queue and ensure a worker is running."""
        queue_key = f"{device_id}:{sender_jid}"

        if queue_key not in self._jid_queues:
            self._jid_queues[queue_key] = asyncio.Queue()

        await self._jid_queues[queue_key].put((text, handler, sender_candidates, reply_jid))

        # Start a worker task for this queue if one isn't already running
        existing = self._jid_workers.get(queue_key)
        if existing is None or existing.done():
            task = asyncio.create_task(
                self._jid_worker(device_id, sender_jid, queue_key)
            )
            self._jid_workers[queue_key] = task

    async def _jid_worker(
        self,
        device_id: str,
        sender_jid: str,
        queue_key: str,
    ) -> None:
        """Sequentially process messages for a single device+JID combination."""
        queue = self._jid_queues.get(queue_key)
        if queue is None:
            return

        while not queue.empty():
            try:
                text, handler, sender_candidates, reply_jid = await queue.get()
                try:
                    # Send composing indicator while the AI is processing
                    try:
                        from neonize.utils.jid import build_jid as _build_jid
                        from neonize.proto.Neonize_pb2 import ChatPresence, ChatPresenceMedia
                        _s_user, _s_server = (
                            sender_jid.rsplit("@", 1) if "@" in sender_jid
                            else (sender_jid, "s.whatsapp.net")
                        )
                        _jid_proto = _build_jid(_s_user, _s_server)
                        _dispatch_client = await self.get_client(device_id)
                        await _dispatch_client.send_chat_presence(
                            _jid_proto,
                            ChatPresence.CHAT_PRESENCE_COMPOSING,
                            ChatPresenceMedia.CHAT_PRESENCE_MEDIA_TEXT,
                        )
                    except Exception as _pe:
                        logger.debug(
                            f"[neonize] Could not send composing presence for {sender_jid}: {_pe}"
                        )

                    logger.info(
                        f"[neonize] Dispatching message from {sender_jid} on device {device_id}: {text[:50]!r}"
                    )
                    if self._app_loop is not None and self._app_loop is not asyncio.get_running_loop():
                        future = asyncio.run_coroutine_threadsafe(
                            handler(
                                device_id=device_id,
                                sender_jid=sender_jid,
                                reply_jid=reply_jid,
                                sender_candidates=sender_candidates,
                                text=text,
                            ),
                            self._app_loop,
                        )
                        await asyncio.wrap_future(future)
                    else:
                        await handler(
                            device_id=device_id,
                            sender_jid=sender_jid,
                            reply_jid=reply_jid,
                            sender_candidates=sender_candidates,
                            text=text,
                        )
                except Exception as e:
                    logger.error(
                        f"[neonize] Worker error processing message from {sender_jid}: {e}",
                        exc_info=True,
                    )
                finally:
                    queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[neonize] _jid_worker unexpected error: {e}", exc_info=True)
