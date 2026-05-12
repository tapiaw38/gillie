import { inject } from 'vue'
import { storeToRefs } from 'pinia'
import { useNotionStore } from '@/stores/notionStore'
import type { INotionService } from '@/services/notion/notionService'

export const useNotion = () => {
  const services = inject<{ notionService: INotionService }>('services')
  if (!services) throw new Error('Services not provided')

  const store = useNotionStore(services.notionService)
  const notionStore = store()

  const {
    authorizationData,
    statusData,
    savedClientId,
    savedRedirectUri,
    hasSecret,
    isConnected,
    workspaceName,
    ownerName,
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
  } = storeToRefs(notionStore)

  const { getCredentials, saveCredentials, getAuthorizationUrl, checkStatus, disconnect } =
    notionStore

  return {
    authorizationData,
    statusData,
    savedClientId,
    savedRedirectUri,
    hasSecret,
    isConnected,
    workspaceName,
    ownerName,
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
    reset: notionStore.$reset,
  }
}
