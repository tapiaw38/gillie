from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.managers.memory_extraction_service import MemoryExtractionService
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.memory import MemoryExtractionError
import logging

logger = logging.getLogger(__name__)


class ExtractMemoryUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory
        self.extraction_service = MemoryExtractionService()

    async def execute(self, user_id: str) -> dict:
        ctx = self.context_factory()
        try:
            conversations = await ctx.repositories.conversation.find_unextracted(user_id)
            if not conversations:
                return {"extracted": 0, "status": "no_new_conversations"}

            openai_client = ctx.integrations.openai
            skill_manager = ctx.platform_managers.skill_manager

            summaries = []
            for conv in conversations:
                summary = await self.extraction_service.summarize_conversation(conv, openai_client)
                if summary:
                    await ctx.repositories.conversation.update_summary(
                        conv.id, summary, memory_extracted=True
                    )
                    summaries.append(summary)
                    logger.info(f"Summarized conversation {conv.id}")

            if summaries:
                await self.extraction_service.update_general_memory(summaries, skill_manager, openai_client)

            return {"extracted": len(summaries), "status": "ok"}

        except NewApplicationError:
            raise
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")
            raise NewApplicationError(MemoryExtractionError, e)
