import logging
from typing import Dict
from src.core.platform.appcontext.appcontext import Factory

logger = logging.getLogger(__name__)


class GetIndexStatusUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str) -> Dict:
        try:
            return self.context_factory.integrations.google_drive.get_index_status(user_id)
        except Exception as e:
            logger.error(f"Error getting Drive index status: {e}", exc_info=True)
            return {"user_id": user_id, "error": str(e)}
