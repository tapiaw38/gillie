import { inject } from 'vue'
import { storeToRefs } from 'pinia'
import { useGmailStore } from '@/stores/gmailStore'
import type { IGmailService } from '@/services/gmail/gmailService'

export const useGmail = () => {
  const services = inject<{ gmailService: IGmailService }>('services')
  if (!services) throw new Error('Services not provided')

  const store = useGmailStore(services.gmailService)
  const gmailStore = store()

  const {
    authorizationData,
    statusData,
    savedClientId,
    savedRedirectUri,
    hasSecret,
    isConnected,
    connectedEmail,
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
  } = storeToRefs(gmailStore)

  const {
    getCredentials,
    saveCredentials,
    getAuthorizationUrl,
    checkStatus,
    disconnect,
  } = gmailStore

  return {
    authorizationData,
    statusData,
    savedClientId,
    savedRedirectUri,
    hasSecret,
    isConnected,
    connectedEmail,
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
    getCredentials,
    saveCredentials,
    getAuthorizationUrl,
    checkStatus,
    disconnect,
    reset: gmailStore.$reset,
  }
}
