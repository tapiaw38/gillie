import { useQuery, useMutation } from '@tanstack/vue-query'
import type { IDriveService } from '@/services/drive/driveService'

export const useDriveQueries = (driveService: IDriveService) => {
  const getCredentialsQuery = useQuery({
    queryKey: ['driveCredentials'],
    queryFn: driveService.getCredentials.bind(driveService),
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
    }) => driveService.saveCredentials(clientId, clientSecret, redirectUri),
  })

  const getAuthorizationUrlMutation = useMutation({
    mutationFn: (profileId?: string) => driveService.getAuthorizationUrl(profileId),
  })

  const checkStatusMutation = useMutation({
    mutationFn: (profileId?: string) => driveService.checkStatus(profileId),
  })

  const disconnectMutation = useMutation({
    mutationFn: driveService.disconnect.bind(driveService),
  })

  return {
    getCredentialsQuery,
    saveCredentialsMutation,
    getAuthorizationUrlMutation,
    checkStatusMutation,
    disconnectMutation,
  }
}
