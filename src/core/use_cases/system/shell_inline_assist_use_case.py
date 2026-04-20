import json
import logging
from typing import Any

from src.core.platform.appcontext.appcontext import Factory
from .terminal_context_formatter import format_terminal_context

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an assistant for a terminal UI. "
    "You will receive the last shell command and recent terminal context. "
    "That context may be raw terminal text or a structured digest with summaries, errors, warnings, important tail lines, and raw references. "
    "Prefer the digest semantics over inventing details. "
    "Return ONLY valid compact JSON with these exact keys: "
    "\"next_command\", \"short_hint\", \"error_hint\". "
    "\"next_command\" must be a single shell command or an empty string. "
    "\"short_hint\" must be a very short plain sentence for normal guidance or empty. "
    "\"error_hint\" must be a very short plain sentence only if the command looks failed, otherwise empty. "
    "Do not use markdown. Do not wrap in code fences. Do not add extra keys."
)


class ShellInlineAssistUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, command: str, terminal_context: Any = "", exit_code: int | None = None) -> dict:
        if not command or not command.strip():
            return {
                "next_command": "",
                "short_hint": "",
                "error_hint": "",
            }

        context_text = format_terminal_context(terminal_context)
        logger.info(
            "[shell_inline_assist] command=%r exit_code=%r context_chars=%d",
            command,
            exit_code,
            len(context_text),
        )
        if context_text:
            user_msg = (
                f"<last_command>{command.strip()}</last_command>\n\n"
                f"<terminal_context>\n{context_text}\n</terminal_context>\n\n"
                f"<exit_code>{'' if exit_code is None else exit_code}</exit_code>"
            )
        else:
            user_msg = (
                f"<last_command>{command.strip()}</last_command>\n\n"
                f"<exit_code>{'' if exit_code is None else exit_code}</exit_code>"
            )

        ctx = self.context_factory()
        raw = await ctx.integrations.openai.simple_completion(
            system=_SYSTEM_PROMPT,
            user=user_msg,
        )
        logger.info(
            "[shell_inline_assist] raw_response_preview=%r",
            (raw or "")[:240],
        )
        if not raw:
            return {
                "next_command": "",
                "short_hint": "",
                "error_hint": "",
            }

        try:
            data = json.loads(raw.strip())
        except Exception:
            return {
                "next_command": "",
                "short_hint": "",
                "error_hint": "",
            }

        return {
            "next_command": str(data.get("next_command", "") or "").strip(),
            "short_hint": str(data.get("short_hint", "") or "").strip(),
            "error_hint": str(data.get("error_hint", "") or "").strip(),
        }
