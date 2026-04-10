import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useCalendarQueries } from '@/queries/calendar'
import type { ICalendarService } from '@/services/calendar/calendarService'
import type {
  CalendarEvent,
  CalendarEventInput,
  CalendarAuthorizationResponse,
  CalendarStatusResponse,
} from '@/types/calendar'

export const useCalendarStore = (calendarService: ICalendarService) =>
  defineStore('calendar', () => {
    const events = ref<CalendarEvent[]>([])
    const authorizationData = ref<CalendarAuthorizationResponse | null>(null)
    const statusData = ref<CalendarStatusResponse | null>(null)
    const savedClientId = ref('')
    const savedRedirectUri = ref('')
    const hasSecret = ref(false)

    const isConnected = computed(() => statusData.value?.is_active ?? false)

    const {
      getCredentialsQuery,
      saveCredentialsMutation,
      getAuthorizationUrlMutation,
      checkStatusMutation,
      createEventMutation,
      listEventsMutation,
      updateEventMutation,
      deleteEventMutation,
      disconnectMutation,
    } = useCalendarQueries(calendarService)

    const getCredentials = async () => {
      try {
        const { data } = await getCredentialsQuery.refetch()
        savedClientId.value = data?.client_id || ''
        savedRedirectUri.value = data?.redirect_uri || ''
        hasSecret.value = data?.has_secret ?? false
      } catch {
        // credentials not configured yet
      }
    }

    const saveCredentials = async (
      clientId: string,
      clientSecret: string,
      redirectUri?: string,
    ) => {
      await saveCredentialsMutation.mutateAsync({ clientId, clientSecret, redirectUri })
    }

    const getAuthorizationUrl = async (profileId?: string) => {
      const response = await getAuthorizationUrlMutation.mutateAsync(profileId)
      authorizationData.value = response
      return response
    }

    const checkStatus = async (profileId?: string) => {
      const response = await checkStatusMutation.mutateAsync(profileId)
      statusData.value = response
      return response
    }

    const disconnect = async () => {
      await disconnectMutation.mutateAsync()
      statusData.value = null
    }

    const createEvent = async (event: CalendarEventInput, profileId?: string) => {
      const response = await createEventMutation.mutateAsync({ event, profileId })
      events.value.push(response.data)
      return response
    }

    const listEvents = async (
      profileId?: string,
      startDate?: string,
      endDate?: string,
      limit?: number,
    ) => {
      const response = await listEventsMutation.mutateAsync({ profileId, startDate, endDate, limit })
      events.value = response.data
      return response
    }

    const updateEvent = async (
      eventId: string,
      event: CalendarEventInput,
      profileId?: string,
    ) => {
      const response = await updateEventMutation.mutateAsync({ eventId, event, profileId })
      const index = events.value.findIndex((e) => e.id === eventId)
      if (index !== -1) events.value[index] = response.data
      return response
    }

    const deleteEvent = async (eventId: string, profileId?: string) => {
      await deleteEventMutation.mutateAsync({ eventId, profileId })
      events.value = events.value.filter((e) => e.id !== eventId)
    }

    return {
      events,
      authorizationData,
      statusData,
      savedClientId,
      savedRedirectUri,
      hasSecret,
      isConnected,

      getCredentials,
      saveCredentials,
      getAuthorizationUrl,
      checkStatus,
      disconnect,
      createEvent,
      listEvents,
      updateEvent,
      deleteEvent,

      isGetCredentialsPending: getCredentialsQuery.isPending,
      isGetCredentialsError: getCredentialsQuery.isError,
      getCredentialsError: getCredentialsQuery.error,

      isSaveCredentialsPending: saveCredentialsMutation.isPending,
      isSaveCredentialsError: saveCredentialsMutation.isError,
      saveCredentialsError: saveCredentialsMutation.error,

      isGetAuthorizationUrlPending: getAuthorizationUrlMutation.isPending,
      isGetAuthorizationUrlError: getAuthorizationUrlMutation.isError,
      getAuthorizationUrlError: getAuthorizationUrlMutation.error,

      isCheckStatusPending: checkStatusMutation.isPending,
      isCheckStatusError: checkStatusMutation.isError,
      checkStatusError: checkStatusMutation.error,

      isDisconnectPending: disconnectMutation.isPending,
      isDisconnectError: disconnectMutation.isError,

      isCreateEventPending: createEventMutation.isPending,
      isCreateEventError: createEventMutation.isError,
      createEventError: createEventMutation.error,

      isListEventsPending: listEventsMutation.isPending,
      isListEventsError: listEventsMutation.isError,
      listEventsError: listEventsMutation.error,

      isUpdateEventPending: updateEventMutation.isPending,
      isUpdateEventError: updateEventMutation.isError,
      updateEventError: updateEventMutation.error,

      isDeleteEventPending: deleteEventMutation.isPending,
      isDeleteEventError: deleteEventMutation.isError,
      deleteEventError: deleteEventMutation.error,
    }
  })
