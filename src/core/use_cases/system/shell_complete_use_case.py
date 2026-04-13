from src.core.platform.appcontext.appcontext import Factory

_SYSTEM_PROMPT = (
    "You are a shell autocomplete engine. "
    "The user has partially typed a shell command. "
    "Return ONLY the text that completes the command after the cursor. "
    "Be concise. No markdown, no explanation, no leading or trailing whitespace, no newline."
)


class ShellCompleteUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, prefix: str) -> str:
        if not prefix or not prefix.strip():
            return ""
        context = self.context_factory()
        suggestion = await context.integrations.openai.simple_completion(
            system=_SYSTEM_PROMPT,
            user=prefix,
        )
        return suggestion.strip()
