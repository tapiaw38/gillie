import { useMutation, useQuery } from '@tanstack/vue-query'
import type { INotionService } from '@/services/notion/notionService'

export const useNotionQueries = (notionService: INotionService) => {
  const getCredentialsQuery = useQuery({
    queryKey: ['notionCredentials'],
    queryFn: notionService.getCredentials.bind(notionService),
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
    }) => notionService.saveCredentials(clientId, clientSecret, redirectUri),
  })

  const getAuthorizationUrlMutation = useMutation({
    mutationFn: (profileId?: string) => notionService.getAuthorizationUrl(profileId),
  })

  const checkStatusMutation = useMutation({
    mutationFn: (profileId?: string) => notionService.checkStatus(profileId),
  })

  const disconnectMutation = useMutation({
    mutationFn: notionService.disconnect.bind(notionService),
  })

  return {
    getCredentialsQuery,
    saveCredentialsMutation,
    getAuthorizationUrlMutation,
    checkStatusMutation,
    disconnectMutation,
  }
}
