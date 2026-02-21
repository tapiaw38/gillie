import { inject } from 'vue'
import { storeToRefs } from 'pinia'
import { useSandboxStore } from '@/stores/sandboxStore'
import type { ISandboxService } from '@/services/sandbox/sandboxService'

export const useSandboxAssistant = () => {
  const services = inject<{ sandboxService: ISandboxService }>('services')
  if (!services) throw new Error('Services not provided')

  const sandboxService = services.sandboxService

  const store = useSandboxStore(sandboxService)
  const sandboxStore = store()

  const {
    conversations,
    currentConversationId,
    messages,
    isLoading,
    isSending,
    isLoadingConversations,
    error,
    currentConversation,
    hasMessages,
    sortedConversations,
  } = storeToRefs(sandboxStore)

  const {
    loadSandboxConversations,
    switchConversation,
    createNewSandboxConversation,
    sendMessage,
    deleteConversation,
    resetCurrentConversation,
    resetStore,
  } = sandboxStore

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
}
