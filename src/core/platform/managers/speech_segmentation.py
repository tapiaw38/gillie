import re

_SENTENCE_END = re.compile(r"[.!?…]+[\"'”’)\]]*\s")
_MIN_SEGMENT_CHARS = 24
_MAX_SEGMENT_CHARS = 320
_SOFT_BREAK = re.compile(r"[,;:][\"'”’)\]]*\s")


def split_leading_sentence(buffer: str) -> tuple[str, str]:
    """Peel off the first speakable segment, leaving the rest buffered.

    Returns ("", buffer) while the buffer is still too short to be worth
    sending to a speech engine on its own.
    """
    if len(buffer) < _MIN_SEGMENT_CHARS:
        return "", buffer

    match = None
    for candidate in _SENTENCE_END.finditer(buffer):
        if candidate.end() >= _MIN_SEGMENT_CHARS:
            match = candidate
            break
    if match:
        return buffer[: match.end()].strip(), buffer[match.end():]

    if len(buffer) < _MAX_SEGMENT_CHARS:
        return "", buffer

    for candidate in _SOFT_BREAK.finditer(buffer):
        if candidate.end() >= _MIN_SEGMENT_CHARS:
            return buffer[: candidate.end()].strip(), buffer[candidate.end():]

    cut = buffer.rfind(" ", _MIN_SEGMENT_CHARS, _MAX_SEGMENT_CHARS)
    if cut == -1:
        cut = _MAX_SEGMENT_CHARS
    return buffer[:cut].strip(), buffer[cut:]
