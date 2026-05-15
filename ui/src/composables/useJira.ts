import { inject } from 'vue'
import { useMutation } from '@tanstack/vue-query'
import type { IJiraService } from '@/services/jira/jiraService'

export const useJira = () => {
  const services = inject<{ jiraService: IJiraService }>('services')
  if (!services) throw new Error('Services not provided')

  const verifyConnectionMutation = useMutation({
    mutationFn: services.jiraService.getProjects.bind(services.jiraService),
  })

  return {
    verifyConnection: verifyConnectionMutation.mutateAsync,
    projects: verifyConnectionMutation.data,
    isVerifyConnectionPending: verifyConnectionMutation.isPending,
    isVerifyConnectionError: verifyConnectionMutation.isError,
    verifyConnectionError: verifyConnectionMutation.error,
  }
}
