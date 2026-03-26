import { ref, computed } from 'vue'
import services from '@/services'
import type {
  CalendarEventInput,
  CalendarEvent,
  CalendarAuthorizationResponse,
  CalendarStatusResponse,
} from '@/types/calendar'

export const useCalendar = () => {
  // State
  const events = ref<CalendarEvent[]>([])
  const authorizationData = ref<CalendarAuthorizationResponse | null>(null)
  const statusData = ref<CalendarStatusResponse | null>(null)
  const isLoading = ref(false)

  // Error states
  const isSaveCredentialsError = ref(false)
  const saveCredentialsError = ref<string>('')

  const isGetAuthUrlError = ref(false)
  const getAuthUrlError = ref<string>('')

  const isCheckStatusError = ref(false)
  const checkStatusError = ref<string>('')

  const isCreateEventError = ref(false)
  const createEventError = ref<string>('')

  const isListEventsError = ref(false)
  const listEventsError = ref<string>('')

  const isUpdateEventError = ref(false)
  const updateEventError = ref<string>('')

  const isDeleteEventError = ref(false)
  const deleteEventError = ref<string>('')

  // Computed
  const isConnected = computed(() => statusData.value?.is_active ?? false)

  // Methods
  const saveCredentials = async (clientId: string, clientSecret: string, redirectUri?: string) => {
    isLoading.value = true
    isSaveCredentialsError.value = false
    saveCredentialsError.value = ''
    try {
      await services.calendarService.saveCredentials(clientId, clientSecret, redirectUri)
    } catch (error: unknown) {
      isSaveCredentialsError.value = true
      saveCredentialsError.value =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.response?.data?.message ||
        (error as Error)?.message ||
        'Error al guardar credenciales'
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const getAuthorizationUrl = async (profileId?: string) => {
    isLoading.value = true
    isGetAuthUrlError.value = false
    getAuthUrlError.value = ''

    try {
      const response = await services.calendarService.getAuthorizationUrl(profileId)
      authorizationData.value = response
      return response
    } catch (error: unknown) {
      isGetAuthUrlError.value = true
      getAuthUrlError.value =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.response?.data?.message ||
        (error as Error)?.message ||
        'Error al obtener URL de autorización'
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const checkStatus = async (profileId?: string) => {
    isLoading.value = true
    isCheckStatusError.value = false
    checkStatusError.value = ''

    try {
      const response = await services.calendarService.checkStatus(profileId)
      statusData.value = response
      return response
    } catch (error: unknown) {
      isCheckStatusError.value = true

      checkStatusError.value =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.response?.data?.message ||
        (error as Error)?.message ||
        'Error al verificar estado'
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const createEvent = async (event: CalendarEventInput, profileId?: string) => {
    isLoading.value = true
    isCreateEventError.value = false
    createEventError.value = ''

    try {
      const response = await services.calendarService.createEvent(event, profileId)
      // Add to local events list
      events.value.push(response.data)
      return response
    } catch (error: unknown) {
      isCreateEventError.value = true
      createEventError.value =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.response?.data?.message ||
        (error as Error)?.message ||
        'Error al crear evento'
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const listEvents = async (
    profileId?: string,
    startDate?: string,
    endDate?: string,
    limit?: number,
  ) => {
    isLoading.value = true
    isListEventsError.value = false
    listEventsError.value = ''

    try {
      const response = await services.calendarService.listEvents(
        profileId,
        startDate,
        endDate,
        limit,
      )
      events.value = response.data
      return response
    } catch (error: unknown) {
      isListEventsError.value = true
      listEventsError.value =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.response?.data?.message ||
        (error as Error)?.message ||
        'Error al listar eventos'
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const updateEvent = async (eventId: string, event: CalendarEventInput, profileId?: string) => {
    isLoading.value = true
    isUpdateEventError.value = false
    updateEventError.value = ''

    try {
      const response = await services.calendarService.updateEvent(eventId, event, profileId)
      const index = events.value.findIndex((e) => e.id === eventId)
      if (index !== -1) {
        events.value[index] = response.data
      }
      return response
    } catch (error: unknown) {
      isUpdateEventError.value = true
      updateEventError.value =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.response?.data?.message ||
        (error as Error)?.message ||
        'Error al actualizar evento'
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const deleteEvent = async (eventId: string, profileId?: string) => {
    isLoading.value = true
    isDeleteEventError.value = false
    deleteEventError.value = ''

    try {
      await services.calendarService.deleteEvent(eventId, profileId)
      events.value = events.value.filter((e) => e.id !== eventId)
    } catch (error: unknown) {
      isDeleteEventError.value = true
      deleteEventError.value =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.response?.data?.message ||
        (error as Error)?.message ||
        'Error al eliminar evento'
      throw error
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    events,
    authorizationData,
    statusData,
    isLoading,
    isConnected,

    // Error states
    isSaveCredentialsError,
    saveCredentialsError,
    isGetAuthUrlError,
    getAuthUrlError,
    isCheckStatusError,
    checkStatusError,
    isCreateEventError,
    createEventError,
    isListEventsError,
    listEventsError,
    isUpdateEventError,
    updateEventError,
    isDeleteEventError,
    deleteEventError,

    // Methods
    saveCredentials,
    getAuthorizationUrl,
    checkStatus,
    createEvent,
    listEvents,
    updateEvent,
    deleteEvent,
  }
}
