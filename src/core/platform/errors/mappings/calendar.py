"""
Calendar Domain Error Mappings
"""
from ..application_error import ErrorDetails

# Session errors
CalendarSessionNotFoundError = ErrorDetails(
    internal_code="calendar:session:not-found",
    status_code=404,
    message="no active Google Calendar session found, please authorize first",
)

CalendarSessionQueryError = ErrorDetails(
    internal_code="calendar:session:query-error",
    status_code=500,
    message="failed to access calendar session",
)

CalendarOAuthError = ErrorDetails(
    internal_code="calendar:oauth:error",
    status_code=500,
    message="Google OAuth authorization failed",
)

CalendarTokenRefreshError = ErrorDetails(
    internal_code="calendar:token:refresh-error",
    status_code=500,
    message="failed to refresh Google Calendar token",
)

# Event errors
CalendarEventTitleRequiredError = ErrorDetails(
    internal_code="calendar:event:title-required",
    status_code=400,
    message="event title is required",
)

CalendarEventTimesRequiredError = ErrorDetails(
    internal_code="calendar:event:times-required",
    status_code=400,
    message="event start_time and end_time are required",
)

CalendarEventInvalidTimesError = ErrorDetails(
    internal_code="calendar:event:invalid-times",
    status_code=400,
    message="end_time must be after start_time",
)

CalendarEventNotFoundError = ErrorDetails(
    internal_code="calendar:event:not-found",
    status_code=404,
    message="calendar event not found",
)

CalendarEventCreateError = ErrorDetails(
    internal_code="calendar:event:create-error",
    status_code=500,
    message="failed to create calendar event",
)

CalendarEventUpdateError = ErrorDetails(
    internal_code="calendar:event:update-error",
    status_code=500,
    message="failed to update calendar event",
)

CalendarEventDeleteError = ErrorDetails(
    internal_code="calendar:event:delete-error",
    status_code=500,
    message="failed to delete calendar event",
)

CalendarEventQueryError = ErrorDetails(
    internal_code="calendar:event:query-error",
    status_code=500,
    message="failed to retrieve calendar events",
)

CalendarSyncError = ErrorDetails(
    internal_code="calendar:sync:error",
    status_code=500,
    message="failed to sync with Google Calendar",
)
