import { useQuery, useMutation } from '@tanstack/vue-query'
import type { IGmailService } from '@/services/gmail/gmailService'

export const useGmailQueries = (gmailService: IGmailService) => {
  const getCredentialsQuery = useQuery({
    queryKey: ['gmailCredentials'],
    queryFn: gmailService.getCredentials.bind(gmailService),
  })

  const saveCredentialsMutation = useMutation({
    mutationFn: ({
      clientId,
      clientSecret,
      redirectUri,
    }: {
      clientId: string
      clientSecret: string
      redirectUri?: string
    }) => gmailService.saveCredentials(clientId, clientSecret, redirectUri),
  })

  const getAuthorizationUrlMutation = useMutation({
    mutationFn: (profileId?: string) => gmailService.getAuthorizationUrl(profileId),
  })

  const checkStatusMutation = useMutation({
    mutationFn: (profileId?: string) => gmailService.checkStatus(profileId),
  })

  const disconnectMutation = useMutation({
    mutationFn: gmailService.disconnect.bind(gmailService),
  })

  return {
    getCredentialsQuery,
    saveCredentialsMutation,
    getAuthorizationUrlMutation,
    checkStatusMutation,
    disconnectMutation,
  }
}
