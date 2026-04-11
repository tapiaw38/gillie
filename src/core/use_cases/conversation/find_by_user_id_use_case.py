from src.schemas import ConversationListOutput
from src.core.platform.appcontext.appcontext import Factory


class FindByUserIdUseCase:
    """
    Use case for finding conversations by user ID.

    This use case follows the Single Responsibility Principle by focusing
    on retrieving and formatting conversation data for a specific user.

    Responsibilities:
    - Retrieve conversations by user ID with optional sandbox filtering
    - Filter sandbox conversations from production queries by default
    - Format conversations for API response
    """

    def __init__(self, context_factory: Factory):
        """
        Initialize the find by user ID use case.

        Args:
            context_factory: Factory for creating context instances
        """
        self.context_factory = context_factory

    def execute(self, user_id: str, include_sandbox: bool = False):
        """
        Executes the find by user ID workflow.

        Args:
            user_id: ID of the user
            include_sandbox: If False (default), returns ONLY production conversations.
                           If True, returns ONLY sandbox conversations.

        Returns:
            ConversationListOutput with matching conversations
        """
        context = self.context_factory()
        conversations = context.repositories.conversation.find_user_id(
            user_id, include_sandbox
        )
        return ConversationListOutput.from_output(conversations)