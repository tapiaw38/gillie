import { inject } from 'vue'
import { storeToRefs } from 'pinia'
import { useDriveStore } from '@/stores/driveStore'
import type { IDriveService } from '@/services/drive/driveService'

export const useDrive = () => {
  const services = inject<{ driveService: IDriveService }>('services')
  if (!services) throw new Error('Services not provided')

  const store = useDriveStore(services.driveService)
  const driveStore = store()

  const {
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
  } = storeToRefs(driveStore)

  const {
    getCredentials,
    saveCredentials,
    getAuthorizationUrl,
    checkStatus,
    disconnect,
  } = driveStore

  return {
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
    getCredentials,
    saveCredentials,
    getAuthorizationUrl,
    checkStatus,
    disconnect,
    reset: driveStore.$reset,
  }
}
