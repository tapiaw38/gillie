<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import ScrollPanel from 'primevue/scrollpanel'
import Toast from 'primevue/toast'
import Card from 'primevue/card'
import { useConversation } from '@/composables/useConversation'
import { useDateFormat } from '@/composables/useDateFormat'
import { useErrorToast } from '@/composables/useErrorToast'
import { onMounted } from 'vue'
import LoadingSpinner from '@/components/core/LoadingSpinner/LoadingSpinner.vue'
import type { AssistantConversation } from '@/types/conversation'

const {
  conversations,
  getUserConversation,
  isGetUserConversationSuccess,
  isGetUserConversationError,
  isGetUserConversationPending,
  getUserConversationError,
} = useConversation()

const { dateFormat } = useDateFormat()

const errorWatchers = [
  {
    flag: isGetUserConversationError,
    summary: 'Error al cargar conversaciones',
    detail: getUserConversationError,
  },
]

const { toast } = useErrorToast(errorWatchers)

onMounted(async () => {
  await getUserConversation()
})

watch(isGetUserConversationSuccess, (value) => {
  if (value) {
    toast.add({
      severity: 'success',
      summary: 'Conversaciones cargadas',
      detail: 'Las conversaciones se han cargado correctamente.',
      life: 3000,
    })
  }
})

const reloadMessages = ref<HTMLElement | null>(null)

const reloadMessagesHandler = async () => {
  reloadMessages.value?.classList.add('spinner-effect')
  try {
    await getUserConversation()
    setTimeout(() => {
      reloadMessages.value?.classList.remove('spinner-effect')
    }, 2000)
    toast.add({
      severity: 'success',
      summary: 'Conversaciones recargadas',
      detail: 'Las conversaciones se han recargado correctamente.',
      life: 3000,
    })
  } catch (error) {
    console.error('Error al obtener conversaciones:', error)
    setTimeout(() => {
      reloadMessages.value?.classList.remove('spinner-effect')
    }, 2000)
  }
}

const conversationSelected = ref<AssistantConversation | undefined>()

const conversationSelectedHandler = computed(() => {
  return (conversationID: string) => {
    conversationSelected.value = conversations?.value?.find(
      (conversation) => conversation.id === conversationID,
    )
  }
})
</script>

<template>
  <div class="conversation-container">
    <!-- Header Section -->
    <div class="header-section">
      <div class="page-header">
        <div class="header-content">
          <div class="icon-wrapper">
            <i class="pi pi-comments"></i>
          </div>
          <div class="title-section">
            <h1 class="page-title">Conversaciones</h1>
            <p class="page-subtitle">Historial de conversaciones del asistente</p>
          </div>
        </div>
        <div class="header-actions">
          <button
            ref="reloadMessages"
            class="refresh-button"
            @click="reloadMessagesHandler"
            title="Recargar conversaciones"
          >
            <i class="pi pi-refresh"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="content-grid">
      <!-- Conversations List -->
      <div class="conversations-panel">
        <div class="panel">
          <div class="panel-header">
            <div class="header-icon conversations-icon">
              <i class="pi pi-list"></i>
            </div>
            <div class="header-text">
              <h3>Lista de Conversaciones</h3>
              <p>{{ conversations?.length || 0 }} conversación(es) encontrada(s)</p>
            </div>
          </div>
          <div class="panel-body">
            <!-- Loading State -->
            <div v-if="isGetUserConversationPending" class="loading-state">
              <LoadingSpinner />
              <p>Cargando conversaciones...</p>
            </div>

            <!-- Error State -->
            <div v-else-if="isGetUserConversationError" class="error-state">
              <i class="pi pi-exclamation-triangle"></i>
              <p>Error al cargar conversaciones</p>
              <small>{{ getUserConversationError }}</small>
            </div>

            <!-- Conversations Table -->
            <div v-else-if="isGetUserConversationSuccess" class="table-wrapper">
              <DataTable
                :value="conversations"
                paginator
                :rows="5"
                :rowsPerPageOptions="[5, 10, 20]"
                class="modern-table"
                :class="{ 'selected-row': conversationSelected }"
              >
                <Column field="title" header="Título" class="title-column">
                  <template #body="slotProps">
                    <div class="conversation-title">
                      <i class="pi pi-comment conversation-icon"></i>
                      <span>{{ slotProps.data.title || 'Sin título' }}</span>
                    </div>
                  </template>
                </Column>
                <Column field="created_at" header="Fecha" class="date-column">
                  <template #body="slotProps">
                    <div class="date-info">
                      <span class="date-text">{{ dateFormat(slotProps.data.created_at) }}</span>
                    </div>
                  </template>
                </Column>
                <Column field="messages" header="Mensajes" class="messages-column">
                  <template #body="slotProps">
                    <div class="message-count">
                      <i class="pi pi-envelope"></i>
                      <span>{{ slotProps.data?.messages?.length || 0 }}</span>
                    </div>
                  </template>
                </Column>
                <Column field="actions" header="Acciones" class="actions-column">
                  <template #body="slotProps">
                    <Button
                      label="Ver"
                      icon="pi pi-eye"
                      class="view-button"
                      size="small"
                      @click="conversationSelectedHandler(slotProps.data.id)"
                    />
                  </template>
                </Column>
              </DataTable>
            </div>
          </div>
        </div>
      </div>

      <!-- Messages Panel -->
      <div class="messages-panel">
        <div class="panel">
          <div class="panel-header">
            <div class="header-icon messages-icon">
              <i class="pi pi-message"></i>
            </div>
            <div class="header-text">
              <h3>
                {{
                  conversationSelected ? 'Historial de Mensajes' : 'Selecciona una Conversación'
                }}
              </h3>
              <p v-if="conversationSelected">
                {{ conversationSelected.messages?.length || 0 }} mensaje(s)
              </p>
              <p v-else>Haz clic en "Ver" para mostrar los mensajes</p>
            </div>
          </div>
          <div class="panel-body">
            <!-- Empty State -->
            <div v-if="!conversationSelected" class="empty-state">
              <i class="pi pi-comments"></i>
              <h4>No hay conversación seleccionada</h4>
              <p>Selecciona una conversación de la lista para ver sus mensajes</p>
            </div>

            <!-- Messages List -->
            <div v-else class="messages-content">
              <div class="messages-scroll">
                <div class="messages-list">
                  <div
                    v-for="message in conversationSelected?.messages"
                    :key="message.created_at"
                    class="message-item"
                    :class="{
                      'user-message': message.sender === 'user',
                      'assistant-message': message.sender === 'assistant',
                    }"
                  >
                    <div class="message-avatar">
                      <i :class="message.sender === 'user' ? 'pi pi-user' : 'pi pi-robot'"></i>
                    </div>
                    <div class="message-bubble">
                      <div class="message-header">
                        <span class="sender-name">
                          {{ message.sender === 'user' ? 'Usuario' : 'Asistente' }}
                        </span>
                        <span class="message-time">
                          {{ dateFormat(message.created_at) }}
                        </span>
                      </div>
                      <div class="message-content">
                        {{ message.content }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Toast for Notifications -->
    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.conversation-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
  background: var(--do-bg);
}

/* Header Section */
.header-section {
  margin-bottom: 2rem;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.04);
  padding: 1rem 1.25rem;
  border-radius: 1rem;
  border: 1px solid var(--do-border-light);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.icon-wrapper {
  width: 3.2rem;
  height: 3.2rem;
  border-radius: 0.875rem;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  color: #fff;
  flex-shrink: 0;
}

.title-section {
  flex: 1;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0 0 0.25rem 0;
}

.page-subtitle {
  font-size: 0.9rem;
  color: var(--do-text-muted);
  margin: 0;
  font-weight: 400;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.refresh-button {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 0.75rem;
  border: none;
  background: var(--gradient-success);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s ease, opacity 0.2s ease;
  font-size: 1.1rem;
}

.refresh-button:hover {
  transform: translateY(-2px);
  opacity: 0.9;
}

.spinner-effect {
  animation: spinner-border 2s linear forwards;
}

@keyframes spinner-border {
  to {
    transform: rotate(360deg);
  }
}

/* Content Grid */
.content-grid {
  display: grid;
  grid-template-columns: 45% 1fr;
  gap: 1.5rem;
}

/* Panel */
.panel {
  border: 1px solid var(--do-border-light);
  border-radius: 0.75rem;
  background: rgba(255, 255, 255, 0.03);
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 1rem 1.25rem;
  background: rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid var(--do-border-light);
}

.panel-body {
  padding: 1.25rem;
}

.header-icon {
  width: 3.2rem;
  height: 3.2rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  color: #fff;
  flex-shrink: 0;
}

.conversations-icon {
  background: var(--gradient-primary);
}

.messages-icon {
  background: var(--gradient-warning);
}

.header-text h3 {
  margin: 0 0 0.2rem 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--do-text);
}

.header-text p {
  margin: 0;
  font-size: 0.8rem;
  color: var(--do-text-muted);
}

/* States */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 3rem 2rem;
  gap: 0.875rem;
}

.loading-state i,
.empty-state i {
  font-size: 3.5rem;
  color: var(--do-text-muted);
}

.error-state i {
  font-size: 3.5rem;
  color: var(--color-danger);
}

.loading-state p,
.error-state p,
.empty-state p {
  margin: 0;
  color: var(--do-text-muted);
  font-weight: 400;
}

.empty-state h4 {
  margin: 0;
  color: var(--do-text);
  font-weight: 600;
}

.error-state small {
  color: var(--color-danger);
  font-size: 0.75rem;
}

/* Table Styles */
.table-wrapper {
  overflow-x: auto;
}

:deep(.modern-table) {
  border-radius: 0.75rem;
  overflow: hidden;
  border: 1px solid var(--do-border-light);
}

:deep(.modern-table .p-datatable-header) {
  background: var(--do-bg);
  border-bottom: 1px solid var(--do-border-light);
  color: var(--do-text);
}

:deep(.modern-table .p-datatable-thead > tr > th) {
  background: rgba(255, 255, 255, 0.05);
  color: var(--do-text);
  font-weight: 600;
  padding: 0.875rem 1rem;
  border-bottom: 2px solid var(--do-border-light);
}

:deep(.modern-table .p-datatable-tbody > tr) {
  background: transparent;
  transition: background 0.2s ease;
}

:deep(.modern-table .p-datatable-tbody > tr:hover) {
  background: rgba(59, 130, 246, 0.07) !important;
}

:deep(.modern-table .p-datatable-tbody > tr > td) {
  padding: 0.875rem 1rem;
  border-bottom: 1px solid var(--do-border-light);
  color: var(--do-text);
  background: transparent;
}

:deep(.modern-table .p-datatable-tbody > tr:last-child > td) {
  border-bottom: none;
}

:deep(.p-paginator) {
  background: var(--do-bg) !important;
  border-color: var(--do-border-light) !important;
  color: var(--do-text) !important;
}

:deep(.p-paginator .p-paginator-pages .p-paginator-page),
:deep(.p-paginator .p-paginator-first),
:deep(.p-paginator .p-paginator-prev),
:deep(.p-paginator .p-paginator-next),
:deep(.p-paginator .p-paginator-last) {
  color: var(--do-text) !important;
  background: transparent !important;
  border-color: var(--do-border-light) !important;
}

:deep(.p-paginator .p-paginator-pages .p-paginator-page.p-highlight) {
  background: var(--color-primary) !important;
  color: #fff !important;
  border-color: var(--color-primary) !important;
}

.conversation-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--do-text);
}

.conversation-icon {
  color: var(--color-primary);
}

.date-info {
  display: flex;
  align-items: center;
}

.date-text {
  font-size: 0.875rem;
  color: var(--do-text-muted);
}

.message-count {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--do-text);
}

.message-count i {
  color: var(--color-warning);
}

:deep(.view-button) {
  background: var(--gradient-success);
  border: none;
  border-radius: 0.5rem;
  padding: 0.4rem 0.875rem;
  font-weight: 500;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

:deep(.view-button:hover) {
  transform: translateY(-1px);
  opacity: 0.9;
}

/* Messages Content */
.messages-content {
  height: 70vh;
  display: flex;
  flex-direction: column;
}

.messages-scroll {
  flex: 1;
  overflow-y: auto;
  max-height: 65vh;
  scrollbar-width: thin;
  scrollbar-color: var(--do-border-light) transparent;
}

.messages-scroll::-webkit-scrollbar {
  width: 6px;
}

.messages-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.messages-scroll::-webkit-scrollbar-thumb {
  background: var(--do-border-light);
  border-radius: 4px;
}

.messages-list {
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.message-item {
  display: flex;
  gap: 0.875rem;
  animation: fadeIn 0.25s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-item.user-message {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  color: #fff;
  flex-shrink: 0;
}

.user-message .message-avatar {
  background: var(--gradient-info);
}

.assistant-message .message-avatar {
  background: var(--gradient-primary);
}

.message-bubble {
  max-width: 72%;
  border-radius: 0.875rem;
  padding: 0.875rem 1rem;
  border: 1px solid var(--do-border-light);
  background: rgba(255, 255, 255, 0.05);
}

.user-message .message-bubble {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.25);
}

.assistant-message .message-bubble {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--do-border-light);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
  gap: 0.5rem;
}

.sender-name {
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--do-text);
}

.user-message .sender-name {
  color: var(--color-info);
}

.message-time {
  font-size: 0.7rem;
  color: var(--do-text-muted);
  white-space: nowrap;
}

.message-content {
  color: var(--do-text);
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-line;
  overflow-wrap: anywhere;
  font-size: 0.9rem;
}

/* Responsive Design */
@media (max-width: 900px) {
  .content-grid {
    grid-template-columns: 1fr;
    gap: 1.25rem;
  }
}

@media (max-width: 768px) {
  .conversation-container {
    padding: 1rem;
  }

  .page-header {
    flex-direction: column;
    gap: 0.875rem;
    text-align: center;
  }

  .header-content {
    flex-direction: column;
    gap: 0.75rem;
  }

  .page-title {
    font-size: 1.3rem;
  }

  .messages-content {
    height: 50vh;
  }

  .messages-scroll {
    max-height: 45vh;
  }

  .message-bubble {
    max-width: 85%;
  }

  :deep(.modern-table .p-datatable-tbody > tr > td),
  :deep(.modern-table .p-datatable-thead > tr > th) {
    padding: 0.625rem 0.5rem;
    font-size: 0.85rem;
  }
}

@media (max-width: 480px) {
  .conversation-container {
    padding: 0.5rem;
  }

  .icon-wrapper {
    width: 2.75rem;
    height: 2.75rem;
    font-size: 1.25rem;
  }

  .page-title {
    font-size: 1.15rem;
  }

  .header-icon {
    width: 2.5rem;
    height: 2.5rem;
    font-size: 1rem;
  }

  .refresh-button {
    width: 2.5rem;
    height: 2.5rem;
    font-size: 1rem;
  }

  .panel-body {
    padding: 1rem;
  }

  .message-item {
    gap: 0.625rem;
  }

  .message-avatar {
    width: 2rem;
    height: 2rem;
    font-size: 0.8rem;
  }

  .message-bubble {
    padding: 0.75rem;
    max-width: 90%;
  }
}
</style>
