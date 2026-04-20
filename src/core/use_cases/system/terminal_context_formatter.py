from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def format_terminal_context(value: Any) -> str:
    """Normalize terminal context into a compact LLM-friendly string.

    Accepts the legacy plain-string format and newer structured digests sent
    by gterm. The output stays deterministic so prompts remain stable.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        logger.info(
            "[terminal_context] kind=string chars=%d preview=%r",
            len(value),
            value[:160],
        )
        return value.strip()
    logger.info(
        "[terminal_context] kind=%s preview=%s",
        type(value).__name__,
        _describe_shape(value),
    )
    rendered = _render_value(value, depth=0)
    logger.info(
        "[terminal_context] rendered_chars=%d rendered_preview=%r",
        len(rendered),
        rendered[:200],
    )
    return rendered.strip()


def _render_value(value: Any, depth: int) -> str:
    if depth > 6:
        return "[max-depth]"

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            rendered = _render_value(item, depth + 1)
            if not rendered:
                continue
            if "\n" in rendered:
                lines.append("- |")
                lines.extend(f"  {line}" for line in rendered.splitlines())
            else:
                lines.append(f"- {rendered}")
        return "\n".join(lines)

    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            rendered = _render_value(item, depth + 1)
            if not rendered:
                continue
            if "\n" in rendered:
                lines.append(f"{key}:")
                lines.extend(f"  {line}" for line in rendered.splitlines())
            else:
                lines.append(f"{key}: {rendered}")
        return "\n".join(lines)

    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value).strip()


def _describe_shape(value: Any) -> str:
    if isinstance(value, dict):
        keys = list(value.keys())
        return f"dict keys={keys[:12]!r}"
    if isinstance(value, list):
        return f"list len={len(value)}"
    return repr(type(value).__name__)
