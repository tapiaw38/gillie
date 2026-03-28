import { ref, computed } from 'vue'
import services from '@/services'
import type { GmailAuthorizationResponse, GmailStatusResponse } from '@/types/gmail'

export const useGmail = () => {
  const authorizationData = ref<GmailAuthorizationResponse | null>(null)
  const statusData = ref<GmailStatusResponse | null>(null)
  const isLoading = ref(false)

  const savedClientId = ref<string>('')
  const savedRedirectUri = ref<string>('')
  const hasSecret = ref(false)

  const isSaveCredentialsError = ref(false)
  const saveCredentialsError = ref<string>('')

  const isGetAuthUrlError = ref(false)
  const getAuthUrlError = ref<string>('')

  const isCheckStatusError = ref(false)
  const checkStatusError = ref<string>('')

  const isConnected = computed(() => statusData.value?.is_active ?? false)
  const connectedEmail = computed(() => statusData.value?.email ?? '')

  const getCredentials = async () => {
    try {
      const data = await services.gmailService.getCredentials()
      savedClientId.value = data.client_id || ''
      savedRedirectUri.value = data.redirect_uri || ''
      hasSecret.value = data.has_secret ?? false
    } catch {}
  }

  const saveCredentials = async (clientId: string, clientSecret: string, redirectUri?: string) => {
    isLoading.value = true
    isSaveCredentialsError.value = false
    saveCredentialsError.value = ''
    try {
      await services.gmailService.saveCredentials(clientId, clientSecret, redirectUri)
    } catch (error: unknown) {
      isSaveCredentialsError.value = true
      saveCredentialsError.value =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.response?.data?.message ||
        (error as Error)?.message ||
        'Error saving credentials'
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
      const response = await services.gmailService.getAuthorizationUrl(profileId)
      authorizationData.value = response
      return response
    } catch (error: unknown) {
      isGetAuthUrlError.value = true
      getAuthUrlError.value =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.response?.data?.message ||
        (error as Error)?.message ||
        'Error getting authorization URL'
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
      const response = await services.gmailService.checkStatus(profileId)
      statusData.value = response
      return response
    } catch (error: unknown) {
      isCheckStatusError.value = true
      checkStatusError.value =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.response?.data?.message ||
        (error as Error)?.message ||
        'Error checking status'
      throw error
    } finally {
      isLoading.value = false
    }
  }

  return {
    authorizationData,
    statusData,
    isLoading,
    isConnected,
    connectedEmail,
    savedClientId,
    savedRedirectUri,
    hasSecret,
    isSaveCredentialsError,
    saveCredentialsError,
    isGetAuthUrlError,
    getAuthUrlError,
    isCheckStatusError,
    checkStatusError,
    getCredentials,
    saveCredentials,
    getAuthorizationUrl,
    checkStatus,
  }
}
