from typing import Any
import logging

from src.core.platform.appcontext.appcontext import Factory
from .terminal_context_formatter import format_terminal_context

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a shell autocomplete engine. "
    "The user has partially typed a shell command. "
    "You may receive recent terminal context either as raw terminal text or as a structured digest. "
    "Return ONLY the text that completes the command after the cursor — "
    "the suffix the user still needs to type. "
    "Be concise. No markdown, no explanation, no leading or trailing whitespace, no newline."
)


class ShellCompleteUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, prefix: str, terminal_context: Any = "") -> str:
        if not prefix or not prefix.strip():
            return ""

        context_text = format_terminal_context(terminal_context)
        logger.info(
            "[shell_complete] prefix=%r context_chars=%d",
            prefix,
            len(context_text),
        )
        if context_text:
            user_msg = (
                f"<terminal_context>\n{context_text}\n</terminal_context>\n\n"
                f"<partial_command>{prefix}</partial_command>"
            )
        else:
            user_msg = f"<partial_command>{prefix}</partial_command>"

        ctx = self.context_factory()
        suggestion = await ctx.integrations.openai.simple_completion(
            system=_SYSTEM_PROMPT,
            user=user_msg,
        )
        return suggestion.strip()
