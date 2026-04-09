import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useDriveQueries } from '@/queries/drive'
import type { IDriveService } from '@/services/drive/driveService'
import type { DriveAuthorizationResponse, DriveStatusResponse } from '@/services/drive/driveService'

export const useDriveStore = (driveService: IDriveService) =>
  defineStore('drive', () => {
    const authorizationData = ref<DriveAuthorizationResponse | null>(null)
    const statusData = ref<DriveStatusResponse | null>(null)
    const savedClientId = ref('')
    const savedRedirectUri = ref('')
    const hasSecret = ref(false)

    const isConnected = computed(() => statusData.value?.is_active ?? false)

    const {
      getCredentialsQuery,
      saveCredentialsMutation,
      getAuthorizationUrlMutation,
      checkStatusMutation,
      disconnectMutation,
    } = useDriveQueries(driveService)

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

    return {
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
    }
  })
