import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import type {
  SandboxConversationResponse,
  SandboxConversationDetailResponse,
  CreateSandboxConversationResponse,
  SandboxMessageResponse,
  CreateSandboxConversationParams,
} from '@/types/sandbox'
import type { ISandboxService } from '@/services/sandbox/sandboxService'

export const useSandboxQueries = (sandboxService: ISandboxService) => {
  const queryClient = useQueryClient()

  const getSandboxConversationsQuery = useQuery<SandboxConversationResponse, Error>({
    queryKey: ['getSandboxConversations'],
    queryFn: sandboxService.getSandboxConversations.bind(sandboxService),
  })

  const getSandboxConversationQuery = (conversationId: string) =>
    useQuery<SandboxConversationDetailResponse, Error>({
      queryKey: ['getSandboxConversation', conversationId],
      queryFn: () => sandboxService.getSandboxConversation(conversationId),
      enabled: !!conversationId,
    })

  const createSandboxConversationMutation = useMutation<
    CreateSandboxConversationResponse,
    Error,
    CreateSandboxConversationParams
  >({
    mutationFn: (params) => sandboxService.createSandboxConversation(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getSandboxConversations'] })
    },
  })

  const sendSandboxMessageMutation = useMutation<
    SandboxMessageResponse,
    Error,
    {
      conversationId: string
      content: string
      context?: string
      hasImageProcessor?: 'activate' | 'deactivate'
      hasTextToVoice?: 'activate' | 'deactivate'
    }
  >({
    mutationFn: ({ conversationId, content, context, hasImageProcessor, hasTextToVoice }) =>
      sandboxService.sendSandboxMessage(
        conversationId,
        content,
        context,
        hasImageProcessor,
        hasTextToVoice,
      ),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['getSandboxConversation', variables.conversationId],
      })
      queryClient.invalidateQueries({ queryKey: ['getSandboxConversations'] })
    },
  })

  const deleteSandboxConversationMutation = useMutation<void, Error, string>({
    mutationFn: (conversationId) => sandboxService.deleteSandboxConversation(conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getSandboxConversations'] })
    },
  })

  return {
    getSandboxConversationsQuery,
    getSandboxConversationQuery,
    createSandboxConversationMutation,
    sendSandboxMessageMutation,
    deleteSandboxConversationMutation,
  }
}
