from src.core.platform.appcontext.appcontext import Factory

_SYSTEM_PROMPT = (
    "You are a shell autocomplete engine. "
    "The user has partially typed a shell command. "
    "You will receive recent terminal output as context and the partial command the user is typing. "
    "Return ONLY the text that completes the command after the cursor — "
    "the suffix the user still needs to type. "
    "Be concise. No markdown, no explanation, no leading or trailing whitespace, no newline."
)


class ShellCompleteUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, prefix: str, terminal_context: str = "") -> str:
        if not prefix or not prefix.strip():
            return ""

        if terminal_context.strip():
            user_msg = (
                f"<terminal_context>\n{terminal_context.strip()}\n</terminal_context>\n\n"
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
