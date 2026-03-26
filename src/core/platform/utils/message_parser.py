"""
Utility for parsing AI response messages into text, image, and document segments.

Detects file URLs embedded in a response and splits the message into
ordered segments so callers can send each part appropriately.
"""

import re
from typing import Dict, List

_URL_BASE = r"https?://[^\s\)\]\"\'<>]+"

# Combined pattern: any file URL with a recognised extension
_ANY_FILE_URL_RE = re.compile(
    _URL_BASE + r"\.(?:jpg|jpeg|png|gif|webp|bmp|svg"
                r"|pdf|doc|docx|xls|xlsx|csv|txt|ppt|pptx"
                r"|zip|tar|gz|json|xml|mp4|mp3|ogg|wav)"
                r"(?:\?[^\s\)\]\"\'<>]*)?",
    re.IGNORECASE,
)

_IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"}


def _classify_url(url: str) -> str:
    """Return 'image' or 'document' based on the URL file extension."""
    ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
    return "image" if ext in _IMAGE_EXTS else "document"


def parse_message_segments(text: str) -> List[Dict[str, str]]:
    """
    Split a message string into ordered text, image, and document segments.

    Each segment is a dict with:
      - "type": "text" | "image" | "document"
      - "content": the text chunk or the file URL

    Example:
        "Reporte: https://cdn.example.com/report.pdf  Foto: https://cdn.example.com/img.png"
        →
        [
            {"type": "text",     "content": "Reporte:"},
            {"type": "document", "content": "https://cdn.example.com/report.pdf"},
            {"type": "text",     "content": "Foto:"},
            {"type": "image",    "content": "https://cdn.example.com/img.png"},
        ]

    If no file URLs are found, returns a single text segment.
    """
    segments: List[Dict[str, str]] = []
    last_end = 0

    for match in _ANY_FILE_URL_RE.finditer(text):
        before = text[last_end : match.start()].strip()
        if before:
            segments.append({"type": "text", "content": before})
        url = match.group(0)
        segments.append({"type": _classify_url(url), "content": url})
        last_end = match.end()

    remaining = text[last_end:].strip()
    if remaining:
        segments.append({"type": "text", "content": remaining})

    return segments if segments else [{"type": "text", "content": text}]
