<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Divider from 'primevue/divider'
import SandboxBanner from '@/components/sandbox/SandboxBanner.vue'
import SandboxConversationList from '@/components/sandbox/SandboxConversationList.vue'
import SandboxChat from '@/components/sandbox/SandboxChat.vue'
import { useSandboxAssistant } from '@/composables/useSandboxAssistant'
import { ApplicationError, getErrorMessage } from '@/types/error'

const confirm = useConfirm()
const toast = useToast()

const {
  currentConversationId,
  messages,
  isLoading,
  isSending,
  isLoadingConversations,
  error,
  currentConversation,
  sortedConversations,
  loadSandboxConversations,
  switchConversation,
  createNewSandboxConversation,
  sendMessage,
  deleteConversation,
  resetStore,
} = useSandboxAssistant()

const isMobileMenuOpen = ref(false)

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
      summary: 'Éxito',
      detail: 'Nueva conversación de prueba creada',
      life: 3000,
    })
    isMobileMenuOpen.value = false
  } catch (err) {
    const errorMessage = err instanceof ApplicationError ? getErrorMessage(err) : 'Error al crear la conversación'
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
    message:
      '¿Estás seguro de que deseas eliminar esta conversación? Esta acción no se puede deshacer.',
    header: 'Eliminar Conversación',
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
          summary: 'Éxito',
          detail: 'Conversación eliminada',
          life: 3000,
        })
      } catch (err) {
        const errorMessage = err instanceof ApplicationError ? getErrorMessage(err) : 'Error al eliminar la conversación'
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

const handleSendMessage = async (content: string) => {
  if (!currentConversationId.value) {
    toast.add({
      severity: 'warn',
      summary: 'Advertencia',
      detail: 'Por favor selecciona o crea una conversación primero',
      life: 3000,
    })
    return
  }

  await sendMessage(content)
}

const handleResetAll = () => {
  confirm.require({
    message:
      '¿Estás seguro de que deseas restablecer todos los datos del sandbox? Esto eliminará todas las conversaciones y no se puede deshacer.',
    header: 'Restablecer Sandbox',
    icon: 'pi pi-exclamation-triangle',
    rejectClass: 'p-button-secondary p-button-outlined',
    rejectLabel: 'Cancelar',
    acceptLabel: 'Restablecer Todo',
    acceptClass: 'p-button-danger',
    accept: async () => {
      resetStore()
      await loadSandboxConversations()
      toast.add({
        severity: 'info',
        summary: 'Restablecido',
        detail: 'Los datos del sandbox han sido restablecidos',
        life: 3000,
      })
    },
  })
}

const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}
</script>

<template>
  <div class="sandbox-view">
    <ConfirmDialog />
    <Toast />

    <div class="sandbox-container">
      <!-- Main Content -->
      <div class="sandbox-content">
        <!-- Mobile Menu Toggle -->
        <div class="mobile-menu-toggle md:hidden">
          <Button
            :icon="isMobileMenuOpen ? 'pi pi-times' : 'pi pi-bars'"
            @click="toggleMobileMenu"
            severity="info"
            outlined
            label="Conversaciones"
          />
        </div>

        <div class="sandbox-layout">
          <!-- Conversation List Sidebar -->
          <div :class="['conversation-sidebar', { 'mobile-open': isMobileMenuOpen }]">
            <SandboxConversationList
              :conversations="sortedConversations"
              :current-conversation-id="currentConversationId"
              :is-loading="isLoadingConversations"
              :error="error"
              @select="handleSelectConversation"
              @create="handleCreateConversation"
              @delete="handleDeleteConversation"
            />

            <Divider />

            <!-- Sandbox Controls -->
            <Card class="sandbox-controls">
              <template #content>
                <div class="controls-content">
                  <h4 class="m-0 mb-3 text-sm font-semibold">Controles del Sandbox</h4>
                  <div class="flex flex-column gap-2">
                    <Button
                      label="Restablecer Todo"
                      icon="pi pi-refresh"
                      @click="handleResetAll"
                      severity="danger"
                      outlined
                      class="p-button-sm w-full"
                    />
                    <Button
                      label="Documentación"
                      icon="pi pi-book"
                      severity="info"
                      outlined
                      class="p-button-sm w-full"
                    />
                  </div>
                </div>
              </template>
            </Card>
          </div>

          <!-- Chat Area -->
          <div class="chat-area">
            <!-- Banner -->
            <div class="sandbox-banner-wrapper">
              <SandboxBanner />
            </div>

            <SandboxChat
              :messages="messages"
              :current-conversation="currentConversation"
              :is-sending="isSending"
              :is-loading="isLoading"
              :error="error"
              @send="handleSendMessage"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sandbox-view {
  height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  background: var(--surface-ground);
  overflow: hidden;
}

.sandbox-container {
  flex: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sandbox-banner-wrapper {
  flex-shrink: 0;
  padding: 1rem;
  background: var(--surface-card);
  border-bottom: 1px solid var(--surface-border);
}

.sandbox-content {
  flex: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.mobile-menu-toggle {
  padding: 1rem;
  background: var(--surface-card);
  border-bottom: 1px solid var(--surface-border);
}

.sandbox-layout {
  flex: 1;
  display: flex;
  flex-direction: row;
  overflow: hidden;
  min-height: 0;
  width: 100%;
}

.conversation-sidebar {
  display: flex;
  flex-direction: column;
  background: var(--surface-card);
  border-right: 1px solid var(--surface-border);
  overflow: hidden;
  width: 350px;
  flex-shrink: 0;
}

.sandbox-controls {
  margin: 1rem;
  background: var(--vt-c-gray-50);
}

:deep(.sandbox-controls .p-card-content) {
  padding: 1rem;
}

.controls-content {
  width: 100%;
}

.controls-content h4 {
  color: var(--vt-c-gray-800);
}

.chat-area {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  flex: 1;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .sandbox-layout {
    position: relative;
  }

  .conversation-sidebar {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1000;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  }

  .conversation-sidebar.mobile-open {
    transform: translateX(0);
  }

  .chat-area {
    width: 100%;
  }
}

/* Tablet Responsive */
@media (min-width: 769px) and (max-width: 1024px) {
  .conversation-sidebar {
    width: 280px;
  }
}

.text-sm {
  font-size: 0.875rem;
}
</style>
