import { ref, computed } from 'vue'
import services from '@/services'
import type { DriveAuthorizationResponse, DriveStatusResponse } from '@/services/drive'

export const useDrive = () => {
  // State
  const authorizationData = ref<DriveAuthorizationResponse | null>(null)
  const statusData = ref<DriveStatusResponse | null>(null)
  const isLoading = ref(false)

  // Credentials state
  const savedClientId = ref<string>('')
  const savedRedirectUri = ref<string>('')
  const hasSecret = ref(false)

  // Error states
  const isSaveCredentialsError = ref(false)
  const saveCredentialsError = ref<string>('')

  const isGetAuthUrlError = ref(false)
  const getAuthUrlError = ref<string>('')

  const isCheckStatusError = ref(false)
  const checkStatusError = ref<string>('')

  // Computed
  const isConnected = computed(() => statusData.value?.is_active ?? false)

  // Methods
  const getCredentials = async () => {
    try {
      const data = await services.driveService.getCredentials()
      savedClientId.value = data.client_id || ''
      savedRedirectUri.value = data.redirect_uri || ''
      hasSecret.value = data.has_secret ?? false
    } catch {
      // ignore — credentials simply not configured yet
    }
  }

  const saveCredentials = async (clientId: string, clientSecret: string, redirectUri?: string) => {
    isLoading.value = true
    isSaveCredentialsError.value = false
    saveCredentialsError.value = ''
    try {
      await services.driveService.saveCredentials(clientId, clientSecret, redirectUri)
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
      const response = await services.driveService.getAuthorizationUrl(profileId)
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
      const response = await services.driveService.checkStatus(profileId)
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

  const disconnect = async () => {
    isLoading.value = true
    try {
      await services.driveService.disconnect()
      statusData.value = null
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    authorizationData,
    statusData,
    isLoading,
    isConnected,
    savedClientId,
    savedRedirectUri,
    hasSecret,

    // Error states
    isSaveCredentialsError,
    saveCredentialsError,
    isGetAuthUrlError,
    getAuthUrlError,
    isCheckStatusError,
    checkStatusError,

    // Methods
    getCredentials,
    saveCredentials,
    getAuthorizationUrl,
    checkStatus,
    disconnect,
  }
}
