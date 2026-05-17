import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ISandboxService } from '@/services/sandbox/sandboxService'
import type { SandboxMessage, SandboxConversation } from '@/types/sandbox'
import { ApplicationError, getErrorMessage } from '@/types/error'

export const useSandboxStore = (sandboxService: ISandboxService) =>
  defineStore('sandbox', () => {
    // State
    const conversations = ref<SandboxConversation[]>([])
    const currentConversationId = ref<string | null>(null)
    const messages = ref<SandboxMessage[]>([])
    const isLoading = ref(false)
    const isSending = ref(false)
    const isLoadingConversations = ref(false)
    const error = ref<string | null>(null)

    // Computed
    const currentConversation = computed(() =>
      conversations.value.find((conv) => conv.id === currentConversationId.value),
    )

    const hasMessages = computed(() => messages.value.length > 0)

    const sortedConversations = computed(() =>
      [...conversations.value].sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      ),
    )

    // Actions
    const loadSandboxConversations = async () => {
      try {
        isLoadingConversations.value = true
        error.value = null

        const response = await sandboxService.getSandboxConversations()
        conversations.value = response.data || []

        // If we have conversations and no current one selected, select the first
        if (conversations.value.length > 0 && !currentConversationId.value) {
          await switchConversation(conversations.value[0].id)
        }
      } catch (err) {
        console.error('Error loading sandbox conversations:', err)
        if (err instanceof ApplicationError) {
          error.value = getErrorMessage(err)
        } else {
          error.value = 'Failed to load conversations'
        }
        conversations.value = []
      } finally {
        isLoadingConversations.value = false
      }
    }

    const switchConversation = async (conversationId: string) => {
      try {
        isLoading.value = true
        error.value = null

        currentConversationId.value = conversationId

        const response = await sandboxService.getSandboxConversation(conversationId)
        messages.value = response.data.messages || []

        const conversationIndex = conversations.value.findIndex((c) => c.id === conversationId)
        if (conversationIndex !== -1) {
          conversations.value[conversationIndex].message_count = messages.value.length
        }
      } catch (err) {
        console.error('Error switching conversation:', err)
        if (err instanceof ApplicationError) {
          error.value = getErrorMessage(err)
        } else {
          error.value = 'Failed to load conversation messages'
        }
        messages.value = []
      } finally {
        isLoading.value = false
      }
    }

    const createNewSandboxConversation = async () => {
      try {
        isLoading.value = true
        error.value = null

        const response = await sandboxService.createSandboxConversation({
          title: 'New Conversation',
          is_sandbox: true,
        })

        const newConversation = response.data
        conversations.value.unshift(newConversation)

        currentConversationId.value = newConversation.id
        messages.value = []

        return newConversation
      } catch (err) {
        console.error('Error creating sandbox conversation:', err)
        if (err instanceof ApplicationError) {
          error.value = getErrorMessage(err)
        } else {
          error.value = 'Failed to create new conversation'
        }
        throw err
      } finally {
        isLoading.value = false
      }
    }

    const sendMessage = async (content: string, context: string = '') => {
      if (!currentConversationId.value) {
        error.value = 'No active conversation'
        return
      }

      try {
        isSending.value = true
        error.value = null

        // Add user message optimistically
        const userMessage: SandboxMessage = {
          id: `temp-${Date.now()}`,
          content,
          sender: 'user',
          created_at: new Date().toISOString(),
        }
        messages.value.push(userMessage)

        // Send message to API
        const response = await sandboxService.sendSandboxMessage(
          currentConversationId.value,
          content,
          context,
        )

        messages.value = messages.value.filter((msg) => msg.id !== userMessage.id)

        if (response.data && response.data.length > 0) {
          const newMessages = response.data.filter(
            (msg) => !messages.value.some((existingMsg) => existingMsg.id === msg.id),
          )
          messages.value.push(...newMessages)
        }

        const conversationIndex = conversations.value.findIndex(
          (c) => c.id === currentConversationId.value,
        )
        if (conversationIndex !== -1) {
          conversations.value[conversationIndex].message_count = messages.value.length
        }
      } catch (err) {
        console.error('Error sending message:', err)
        if (err instanceof ApplicationError) {
          error.value = getErrorMessage(err)
        } else {
          error.value = 'Failed to send message'
        }
        messages.value = messages.value.filter((msg) => !msg.id.startsWith('temp-'))
      } finally {
        isSending.value = false
      }
    }

    const deleteConversation = async (conversationId: string) => {
      try {
        error.value = null

        await sandboxService.deleteSandboxConversation(conversationId)

        // Remove from local state
        conversations.value = conversations.value.filter((conv) => conv.id !== conversationId)

        // If deleted conversation was current, switch to another one
        if (currentConversationId.value === conversationId) {
          if (conversations.value.length > 0) {
            await switchConversation(conversations.value[0].id)
          } else {
            currentConversationId.value = null
            messages.value = []
          }
        }
      } catch (err) {
        console.error('Error deleting conversation:', err)
        if (err instanceof ApplicationError) {
          error.value = getErrorMessage(err)
        } else {
          error.value = 'Failed to delete conversation'
        }
        throw err
      }
    }

    const resetCurrentConversation = () => {
      currentConversationId.value = null
      messages.value = []
    }

    const resetStore = () => {
      conversations.value = []
      currentConversationId.value = null
      messages.value = []
      isLoading.value = false
      isSending.value = false
      isLoadingConversations.value = false
      error.value = null
    }

    return {
      // State
      conversations,
      currentConversationId,
      messages,
      isLoading,
      isSending,
      isLoadingConversations,
      error,

      // Computed
      currentConversation,
      hasMessages,
      sortedConversations,

      // Actions
      loadSandboxConversations,
      switchConversation,
      createNewSandboxConversation,
      sendMessage,
      deleteConversation,
      resetCurrentConversation,
      resetStore,
    }
  })
