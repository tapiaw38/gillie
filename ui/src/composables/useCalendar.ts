import { inject } from 'vue'
import { storeToRefs } from 'pinia'
import { useCalendarStore } from '@/stores/calendarStore'
import type { ICalendarService } from '@/services/calendar/calendarService'

export const useCalendar = () => {
  const services = inject<{ calendarService: ICalendarService }>('services')
  if (!services) throw new Error('Services not provided')

  const store = useCalendarStore(services.calendarService)
  const calendarStore = store()

  const {
    events,
    authorizationData,
    statusData,
    savedClientId,
    savedRedirectUri,
    hasSecret,
    isConnected,
    isGetCredentialsPending,
    isGetCredentialsError,
    getCredentialsError,
    isSaveCredentialsPending,
    isSaveCredentialsError,
    saveCredentialsError,
    isGetAuthorizationUrlPending,
    isGetAuthorizationUrlError,
    getAuthorizationUrlError,
    isCheckStatusPending,
    isCheckStatusError,
    checkStatusError,
    isDisconnectPending,
    isDisconnectError,
    isCreateEventPending,
    isCreateEventError,
    createEventError,
    isListEventsPending,
    isListEventsError,
    listEventsError,
    isUpdateEventPending,
    isUpdateEventError,
    updateEventError,
    isDeleteEventPending,
    isDeleteEventError,
    deleteEventError,
  } = storeToRefs(calendarStore)

  const {
    getCredentials,
    saveCredentials,
    getAuthorizationUrl,
    checkStatus,
    disconnect,
    createEvent,
    listEvents,
    updateEvent,
    deleteEvent,
  } = calendarStore

  return {
    events,
    authorizationData,
    statusData,
    savedClientId,
    savedRedirectUri,
    hasSecret,
    isConnected,
    isGetCredentialsPending,
    isGetCredentialsError,
    getCredentialsError,
    isSaveCredentialsPending,
    isSaveCredentialsError,
    saveCredentialsError,
    isGetAuthorizationUrlPending,
    isGetAuthorizationUrlError,
    getAuthorizationUrlError,
    isCheckStatusPending,
    isCheckStatusError,
    checkStatusError,
    isDisconnectPending,
    isDisconnectError,
    isCreateEventPending,
    isCreateEventError,
    createEventError,
    isListEventsPending,
    isListEventsError,
    listEventsError,
    isUpdateEventPending,
    isUpdateEventError,
    updateEventError,
    isDeleteEventPending,
    isDeleteEventError,
    deleteEventError,
    getCredentials,
    saveCredentials,
    getAuthorizationUrl,
    checkStatus,
    disconnect,
    createEvent,
    listEvents,
    updateEvent,
    deleteEvent,
    reset: calendarStore.$reset,
  }
}
