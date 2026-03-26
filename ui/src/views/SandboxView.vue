<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import Button from 'primevue/button'
import SandboxConversationList from '@/components/sandbox/SandboxConversationList.vue'
import SandboxChat from '@/components/sandbox/SandboxChat.vue'
import { useSandboxAssistant } from '@/composables/useSandboxAssistant'
import { useApiKey } from '@/composables/useApiKey'
import { ApplicationError, getErrorMessage } from '@/types/error'

const confirm = useConfirm()
const toast = useToast()
const { getApiKey } = useApiKey()

const {
  currentConversationId,
  messages: storeMessages,
  isLoadingConversations,
  error,
  currentConversation,
  sortedConversations,
  loadSandboxConversations,
  switchConversation,
  createNewSandboxConversation,
  deleteConversation,
} = useSandboxAssistant()

const isMobileMenuOpen = ref(false)

const apiKey = computed(() => getApiKey())

const assistantName = computed(() => {
  return currentConversation.value?.title ?? 'Chat con el asistente'
})

onMounted(async () => {
  await loadSandboxConversations()
})

const handleSelectConversation = async (conversationId: string) => {
  await switchConversation(conversationId)
  isMobileMenuOpen.value = false
}

const handleCreateConversation = async () => {
  try {
    await createNewSandboxConversation()
    toast.add({
      severity: 'success',
      summary: 'Nueva conversación',
      detail: 'Conversación creada correctamente',
      life: 3000,
    })
    isMobileMenuOpen.value = false
  } catch (err) {
    const errorMessage =
      err instanceof ApplicationError ? getErrorMessage(err) : 'Error al crear la conversación'
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorMessage,
      life: 3000,
    })
  }
}

const handleDeleteConversation = (conversationId: string) => {
  confirm.require({
    message: '¿Deseas eliminar esta conversación? Esta acción no se puede deshacer.',
    header: 'Eliminar conversación',
    icon: 'pi pi-exclamation-triangle',
    rejectClass: 'p-button-secondary p-button-outlined',
    rejectLabel: 'Cancelar',
    acceptLabel: 'Eliminar',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await deleteConversation(conversationId)
        toast.add({
          severity: 'success',
          summary: 'Eliminada',
          detail: 'Conversación eliminada',
          life: 3000,
        })
      } catch (err) {
        const errorMessage =
          err instanceof ApplicationError
            ? getErrorMessage(err)
            : 'Error al eliminar la conversación'
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: errorMessage,
          life: 3000,
        })
      }
    },
  })
}

const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}
</script>

<template>
  <div class="chat-view">
    <ConfirmDialog />
    <Toast />

    <!-- Mobile header bar -->
    <div class="mobile-topbar">
      <Button
        :icon="isMobileMenuOpen ? 'pi pi-times' : 'pi pi-bars'"
        @click="toggleMobileMenu"
        severity="info"
        text
        aria-label="Menú de conversaciones"
      />
      <span class="mobile-topbar-title">{{ assistantName }}</span>
      <Button
        icon="pi pi-plus"
        @click="handleCreateConversation"
        severity="info"
        text
        aria-label="Nueva conversación"
      />
    </div>

    <div class="chat-layout">
      <!-- Sidebar -->
      <aside :class="['chat-sidebar', { 'chat-sidebar--open': isMobileMenuOpen }]">
        <!-- Sidebar header -->
        <div class="sidebar-header">
          <h2 class="sidebar-title">Conversaciones</h2>
          <Button
            icon="pi pi-plus"
            label="Nueva"
            severity="info"
            size="small"
            @click="handleCreateConversation"
          />
        </div>

        <!-- Conversation list -->
        <div class="sidebar-list">
          <SandboxConversationList
            :conversations="sortedConversations"
            :current-conversation-id="currentConversationId"
            :is-loading="isLoadingConversations"
            :error="error"
            @select="handleSelectConversation"
            @create="handleCreateConversation"
            @delete="handleDeleteConversation"
          />
        </div>
      </aside>

      <!-- Mobile overlay -->
      <div
        v-if="isMobileMenuOpen"
        class="sidebar-overlay"
        @click="isMobileMenuOpen = false"
      />

      <!-- Main chat area -->
      <main class="chat-main">
        <!-- Chat header -->
        <div class="chat-header">
          <div class="chat-header-info">
            <i class="pi pi-microchip-ai chat-header-icon" />
            <div>
              <h3 class="chat-header-title">{{ assistantName }}</h3>
              <p v-if="currentConversationId" class="chat-header-subtitle">
                <span class="status-dot status-dot--online" />
                En línea
              </p>
            </div>
          </div>

        </div>

        <!-- Chat component -->
        <div class="chat-body">
          <SandboxChat
            :conversation-id="currentConversationId"
            :api-key="apiKey"
            :initial-messages="storeMessages"
            @message-sent="() => {}"
          />
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
/* ── Root ─────────────────────────────────────────────────────────────── */
.chat-view {
  height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  background: var(--do-bg);
  overflow: hidden;
}

/* ── Mobile topbar (hidden on desktop) ────────────────────────────────── */
.mobile-topbar {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background: rgba(13, 27, 46, 0.95);
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  flex-shrink: 0;
}

.mobile-topbar-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--do-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 60%;
}

/* ── Layout ───────────────────────────────────────────────────────────── */
.chat-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
  position: relative;
}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
.chat-sidebar {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: rgba(13, 27, 46, 0.8);
  border-right: 1px solid rgba(255, 255, 255, 0.07);
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1rem 0.75rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
}

.sidebar-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--do-text-secondary);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.sidebar-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-list::-webkit-scrollbar {
  width: 3px;
}

.sidebar-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 2px;
}

/* ── Mobile sidebar overlay ───────────────────────────────────────────── */
.sidebar-overlay {
  display: none;
}

/* ── Main area ────────────────────────────────────────────────────────── */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* ── Chat header ──────────────────────────────────────────────────────── */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem;
  background: rgba(13, 27, 46, 0.6);
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  flex-shrink: 0;
  gap: 1rem;
}

.chat-header-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.chat-header-icon {
  font-size: 1.25rem;
  color: var(--do-success);
  opacity: 0.85;
}

.chat-header-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--do-text);
  margin: 0;
}

.chat-header-subtitle {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: var(--do-text-muted);
  margin: 0;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot--online {
  background: var(--do-success);
  box-shadow: 0 0 5px rgba(10, 207, 131, 0.5);
}

/* ── Chat body ────────────────────────────────────────────────────────── */
.chat-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ── Responsive ───────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .mobile-topbar {
    display: flex;
  }

  .chat-sidebar {
    position: absolute;
    top: 0;
    left: 0;
    width: 85%;
    max-width: 320px;
    height: 100%;
    z-index: 200;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    background: var(--do-bg-white);
  }

  .chat-sidebar--open {
    transform: translateX(0);
  }

  .sidebar-overlay {
    display: block;
    position: absolute;
    inset: 0;
    z-index: 199;
    background: rgba(0, 0, 0, 0.5);
  }

  .chat-header {
    padding: 0.6rem 1rem;
  }

  .new-conv-btn {
    display: none;
  }
}

@media (min-width: 769px) and (max-width: 1024px) {
  .chat-sidebar {
    width: 240px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .chat-sidebar {
    transition: none;
  }
}
</style>
