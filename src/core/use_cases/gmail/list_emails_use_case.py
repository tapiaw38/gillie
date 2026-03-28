import logging
from typing import Optional, List, Dict, Any

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.gmail import GmailEmailQueryError

logger = logging.getLogger(__name__)


class ListEmailsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(
        self,
        user_id: str,
        query: str = "",
        max_results: int = 20,
        label_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            return self.context_factory.integrations.gmail.list_emails(
                user_id=user_id,
                query=query,
                max_results=max_results,
                label_ids=label_ids,
            )
        except Exception as e:
            logger.error(f"Error listing Gmail emails: {e}", exc_info=True)
            raise NewApplicationError(GmailEmailQueryError, e)
