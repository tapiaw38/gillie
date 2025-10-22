"""
FAQ Domain Error Mappings

Errors related to FAQ (Frequently Asked Questions) management operations.
"""

from ..application_error import ErrorDetails


# FAQ Create Errors
FAQCreateQueryError = ErrorDetails(
    internal_code="faq:create:query-error",
    status_code=500,
    message="failed to create FAQ"
)

FAQCreateValidationError = ErrorDetails(
    internal_code="faq:create:validation-error",
    status_code=400,
    message="invalid FAQ data"
)

FAQCreateQuestionRequiredError = ErrorDetails(
    internal_code="faq:create:question-required",
    status_code=400,
    message="FAQ question is required"
)

FAQCreateAnswerRequiredError = ErrorDetails(
    internal_code="faq:create:answer-required",
    status_code=400,
    message="FAQ answer is required"
)

FAQCreateCategoryRequiredError = ErrorDetails(
    internal_code="faq:create:category-required",
    status_code=400,
    message="FAQ category is required"
)

FAQCreateDuplicateError = ErrorDetails(
    internal_code="faq:create:duplicate",
    status_code=409,
    message="FAQ with this question already exists"
)

FAQCreateNotFoundAfterCreationError = ErrorDetails(
    internal_code="faq:create:not-found-after-creation",
    status_code=500,
    message="FAQ not found after creation"
)

# FAQ Get Errors
FAQGetQueryError = ErrorDetails(
    internal_code="faq:get:query-error",
    status_code=500,
    message="failed to retrieve FAQ"
)

FAQGetNotFoundError = ErrorDetails(
    internal_code="faq:get:not-found",
    status_code=404,
    message="FAQ not found"
)

# FAQ Update Errors
FAQUpdateQueryError = ErrorDetails(
    internal_code="faq:update:query-error",
    status_code=500,
    message="failed to update FAQ"
)

FAQUpdateNotFoundError = ErrorDetails(
    internal_code="faq:update:not-found",
    status_code=404,
    message="FAQ not found for update"
)

FAQUpdateValidationError = ErrorDetails(
    internal_code="faq:update:validation-error",
    status_code=400,
    message="invalid update data"
)

# FAQ Delete Errors
FAQDeleteQueryError = ErrorDetails(
    internal_code="faq:delete:query-error",
    status_code=500,
    message="failed to delete FAQ"
)

FAQDeleteNotFoundError = ErrorDetails(
    internal_code="faq:delete:not-found",
    status_code=404,
    message="FAQ not found for deletion"
)

# FAQ List Errors
FAQListQueryError = ErrorDetails(
    internal_code="faq:list:query-error",
    status_code=500,
    message="failed to retrieve FAQs"
)

FAQListByCategoryQueryError = ErrorDetails(
    internal_code="faq:list-by-category:query-error",
    status_code=500,
    message="failed to retrieve FAQs by category"
)

FAQListByCategoryNotFoundError = ErrorDetails(
    internal_code="faq:list-by-category:not-found",
    status_code=404,
    message="no FAQs found for this category"
)
