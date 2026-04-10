import { useQuery, useMutation } from '@tanstack/vue-query'
import type { ICalendarService } from '@/services/calendar/calendarService'
import type { CalendarEventInput } from '@/types/calendar'

export const useCalendarQueries = (calendarService: ICalendarService) => {
  const getCredentialsQuery = useQuery({
    queryKey: ['calendarCredentials'],
    queryFn: calendarService.getCredentials.bind(calendarService),
  })

  const saveCredentialsMutation = useMutation({
    mutationFn: ({
      clientId,
      clientSecret,
      redirectUri,
    }: {
      clientId: string
      clientSecret: string
      redirectUri?: string
    }) => calendarService.saveCredentials(clientId, clientSecret, redirectUri),
  })

  const getAuthorizationUrlMutation = useMutation({
    mutationFn: (profileId?: string) => calendarService.getAuthorizationUrl(profileId),
  })

  const checkStatusMutation = useMutation({
    mutationFn: (profileId?: string) => calendarService.checkStatus(profileId),
  })

  const createEventMutation = useMutation({
    mutationFn: ({
      event,
      profileId,
    }: {
      event: CalendarEventInput
      profileId?: string
    }) => calendarService.createEvent(event, profileId),
  })

  const listEventsMutation = useMutation({
    mutationFn: ({
      profileId,
      startDate,
      endDate,
      limit,
    }: {
      profileId?: string
      startDate?: string
      endDate?: string
      limit?: number
    }) => calendarService.listEvents(profileId, startDate, endDate, limit),
  })

  const updateEventMutation = useMutation({
    mutationFn: ({
      eventId,
      event,
      profileId,
    }: {
      eventId: string
      event: CalendarEventInput
      profileId?: string
    }) => calendarService.updateEvent(eventId, event, profileId),
  })

  const deleteEventMutation = useMutation({
    mutationFn: ({ eventId, profileId }: { eventId: string; profileId?: string }) =>
      calendarService.deleteEvent(eventId, profileId),
  })

  const disconnectMutation = useMutation({
    mutationFn: calendarService.disconnect.bind(calendarService),
  })

  return {
    getCredentialsQuery,
    saveCredentialsMutation,
    getAuthorizationUrlMutation,
    checkStatusMutation,
    createEventMutation,
    listEventsMutation,
    updateEventMutation,
    deleteEventMutation,
    disconnectMutation,
  }
}
