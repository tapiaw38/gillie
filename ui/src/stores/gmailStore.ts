import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useGmailQueries } from '@/queries/gmail'
import type { IGmailService } from '@/services/gmail/gmailService'
import type { GmailAuthorizationResponse, GmailStatusResponse } from '@/types/gmail'

export const useGmailStore = (gmailService: IGmailService) =>
  defineStore('gmail', () => {
    const authorizationData = ref<GmailAuthorizationResponse | null>(null)
    const statusData = ref<GmailStatusResponse | null>(null)
    const savedClientId = ref('')
    const savedRedirectUri = ref('')
    const hasSecret = ref(false)

    const isConnected = computed(() => statusData.value?.is_active ?? false)
    const connectedEmail = computed(() => statusData.value?.email ?? '')

    const {
      getCredentialsQuery,
      saveCredentialsMutation,
      getAuthorizationUrlMutation,
      checkStatusMutation,
      disconnectMutation,
    } = useGmailQueries(gmailService)

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
      connectedEmail,

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
