import { defineStore } from 'pinia'
import { useConversationQueries } from '@/queries/conversation'
import type { IConversationService } from '@/services/conversation/conversationService'
import type { AssistantConversation } from '@/types/conversation'
import { ref } from 'vue'

export const useConversationStore = (conversationService: IConversationService) =>
  defineStore('conversationStore', () => {
    const conversations = ref<AssistantConversation[] | null | undefined>(null)

    const { getUserConversationQuery } = useConversationQueries(conversationService)

    const getUserConversation = async () => {
      try {
        const { data } = await getUserConversationQuery.refetch()
        conversations.value = data?.data
      } catch (error) {
        console.error('Failed to fetch conversation data:', error)
        throw error
      }
    }

    const isDeleteConversationPending = ref(false)
    const isDeleteConversationError = ref(false)
    const deleteConversationError = ref<string | null>(null)

    const deleteConversation = async (conversationId: string) => {
      isDeleteConversationPending.value = true
      isDeleteConversationError.value = false
      deleteConversationError.value = null
      try {
        await conversationService.deleteConversation(conversationId)
        conversations.value = conversations.value?.filter((c) => c.id !== conversationId) ?? null
      } catch (error) {
        isDeleteConversationError.value = true
        deleteConversationError.value =
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (error as any)?.response?.data?.message ?? (error as Error)?.message ?? 'Error'
        throw error
      } finally {
        isDeleteConversationPending.value = false
      }
    }

    return {
      conversations,
      getUserConversation,
      deleteConversation,

      isGetUserConversationPending: getUserConversationQuery.isPending,
      isGetUserConversationSuccess: getUserConversationQuery.isSuccess,
      isGetUserConversationError: getUserConversationQuery.isError,
      getUserConversationError: getUserConversationQuery.error,

      isDeleteConversationPending,
      isDeleteConversationError,
      deleteConversationError,
    }
  })
