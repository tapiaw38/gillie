"""Memory / Skills error mappings."""

from src.core.platform.errors.application_error import ErrorDetails

MemoryFAQNotFoundError = ErrorDetails(
    internal_code="memory:faq:not-found",
    status_code=404,
    message="FAQ not found",
)

MemoryFAQCreateError = ErrorDetails(
    internal_code="memory:faq:create-error",
    status_code=500,
    message="Failed to create FAQ",
)

MemoryFAQUpdateError = ErrorDetails(
    internal_code="memory:faq:update-error",
    status_code=500,
    message="Failed to update FAQ",
)

MemoryFAQDeleteError = ErrorDetails(
    internal_code="memory:faq:delete-error",
    status_code=500,
    message="Failed to delete FAQ",
)

MemorySkillNotFoundError = ErrorDetails(
    internal_code="memory:skill:not-found",
    status_code=404,
    message="Skill not found",
)

MemoryExtractionError = ErrorDetails(
    internal_code="memory:extract:error",
    status_code=500,
    message="Failed to extract memory from conversations",
)
