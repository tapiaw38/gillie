"""
Utility for parsing AI response messages into text and image segments.

Detects image URLs embedded in a response and splits the message into
ordered segments so callers can send each part appropriately.
"""

import re
from typing import Dict, List

# Matches http/https URLs ending in common image extensions (with optional query string)
_IMAGE_URL_RE = re.compile(
    r"https?://[^\s\)\]\"\'<>]+\.(?:jpg|jpeg|png|gif|webp|bmp|svg)(?:\?[^\s\)\]\"\'<>]*)?",
    re.IGNORECASE,
)


def parse_message_segments(text: str) -> List[Dict[str, str]]:
    """
    Split a message string into ordered text and image segments.

    Each segment is a dict with:
      - "type": "text" | "image"
      - "content": the text chunk or the image URL

    Example:
        "Aquí está el producto: https://example.com/img.png Precio: $5"
        →
        [
            {"type": "text",  "content": "Aquí está el producto:"},
            {"type": "image", "content": "https://example.com/img.png"},
            {"type": "text",  "content": "Precio: $5"},
        ]

    If no image URLs are found, returns a single text segment.
    """
    segments: List[Dict[str, str]] = []
    last_end = 0

    for match in _IMAGE_URL_RE.finditer(text):
        before = text[last_end : match.start()].strip()
        if before:
            segments.append({"type": "text", "content": before})
        segments.append({"type": "image", "content": match.group(0)})
        last_end = match.end()

    remaining = text[last_end:].strip()
    if remaining:
        segments.append({"type": "text", "content": remaining})

    return segments if segments else [{"type": "text", "content": text}]
