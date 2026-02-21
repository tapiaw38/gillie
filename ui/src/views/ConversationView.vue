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
            <p class="page-subtitle">Gestiona y revisa todas las conversaciones con tus clientes</p>
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
        <Card class="conversations-card">
          <template #header>
            <div class="card-header">
              <div class="header-icon conversations-icon">
                <i class="pi pi-list"></i>
              </div>
              <div class="header-text">
                <h3>Lista de Conversaciones</h3>
                <p>{{ conversations?.length || 0 }} conversación(es) encontrada(s)</p>
              </div>
            </div>
          </template>
          <template #content>
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
          </template>
        </Card>
      </div>

      <!-- Messages Panel -->
      <div class="messages-panel">
        <Card class="messages-card">
          <template #header>
            <div class="card-header">
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
          </template>
          <template #content>
            <!-- Empty State -->
            <div v-if="!conversationSelected" class="empty-state">
              <i class="pi pi-comments"></i>
              <h4>No hay conversación seleccionada</h4>
              <p>Selecciona una conversación de la lista para ver sus mensajes</p>
            </div>

            <!-- Messages List -->
            <div v-else class="messages-content">
              <ScrollPanel class="messages-scroll">
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
              </ScrollPanel>
            </div>
          </template>
        </Card>
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
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
}

/* Header Section */
.header-section {
  margin-bottom: 2rem;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.icon-wrapper {
  width: 4rem;
  height: 4rem;
  border-radius: 1rem;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: white;
  box-shadow: var(--shadow-primary);
}

.title-section {
  flex: 1;
}

.page-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 0.5rem 0;
  background: linear-gradient(135deg, #1e293b 0%, #475569 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-subtitle {
  font-size: 1.125rem;
  color: #64748b;
  margin: 0;
  font-weight: 400;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.refresh-button {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  border: none;
  background: var(--gradient-success);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 1.25rem;
  box-shadow: var(--shadow-success);
}

.refresh-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(16, 185, 129, 0.4);
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
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

/* Card Styles */
.conversations-card,
.messages-card {
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
  height: fit-content;
}

.conversations-card:hover,
.messages-card:hover {
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

:deep(.conversations-card .p-card-header),
:deep(.messages-card .p-card-header) {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e2e8f0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  color: white;
}

.conversations-icon {
  background: var(--gradient-primary);
}

.messages-icon {
  background: var(--gradient-warning);
}

.header-text h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #374151;
}

.header-text p {
  margin: 0;
  font-size: 0.875rem;
  color: #64748b;
}

:deep(.conversations-card .p-card-content),
:deep(.messages-card .p-card-content) {
  padding: 2rem;
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
  gap: 1rem;
}

.loading-state i,
.error-state i,
.empty-state i {
  font-size: 3rem;
  color: #94a3b8;
}

.error-state i {
  color: var(--color-danger);
}

.loading-state p,
.error-state p,
.empty-state p {
  margin: 0;
  color: #64748b;
  font-weight: 500;
}

.empty-state h4 {
  margin: 0;
  color: #374151;
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
  border: 1px solid #e2e8f0;
}

:deep(.modern-table .p-datatable-header) {
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

:deep(.modern-table .p-datatable-thead > tr > th) {
  background: #f1f5f9;
  color: #374151;
  font-weight: 600;
  padding: 1rem;
  border-bottom: 2px solid #e2e8f0;
}

:deep(.modern-table .p-datatable-tbody > tr) {
  transition: all 0.3s ease;
}

:deep(.modern-table .p-datatable-tbody > tr:hover) {
  background: #f8fafc;
}

:deep(.modern-table .p-datatable-tbody > tr > td) {
  padding: 1rem;
  border-bottom: 1px solid #f1f5f9;
}

.conversation-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
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
  color: #64748b;
}

.message-count {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #374151;
}

.message-count i {
  color: var(--color-warning);
}

:deep(.view-button) {
  background: var(--gradient-success);
  border: none;
  border-radius: 0.5rem;
  padding: 0.5rem 1rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

:deep(.view-button:hover) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-success);
}

/* Messages Content */
.messages-content {
  height: 600px;
  display: flex;
  flex-direction: column;
}

:deep(.messages-scroll) {
  height: 100%;
  flex: 1;
}

:deep(.messages-scroll .p-scrollpanel-wrapper) {
  border-right: none;
}

:deep(.messages-scroll .p-scrollpanel-bar-y) {
  background: #e2e8f0;
  border-radius: 4px;
  width: 6px;
}

.messages-list {
  padding: 1rem;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-radius: 0.75rem;
  min-height: 100%;
}

.message-item {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
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
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  color: white;
  flex-shrink: 0;
}

.user-message .message-avatar {
  background: var(--gradient-info);
}

.assistant-message .message-avatar {
  background: var(--gradient-primary);
}

.message-bubble {
  max-width: 70%;
  background: white;
  border-radius: 1rem;
  padding: 1rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
  position: relative;
}

.user-message .message-bubble {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  border-color: var(--color-info);
}

.user-message .message-bubble::after {
  content: '';
  position: absolute;
  top: 1rem;
  right: -8px;
  width: 0;
  height: 0;
  border-left: 8px solid #bfdbfe;
  border-top: 8px solid transparent;
  border-bottom: 8px solid transparent;
}

.assistant-message .message-bubble::after {
  content: '';
  position: absolute;
  top: 1rem;
  left: -8px;
  width: 0;
  height: 0;
  border-right: 8px solid white;
  border-top: 8px solid transparent;
  border-bottom: 8px solid transparent;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.sender-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: #374151;
}

.user-message .sender-name {
  color: var(--color-info-dark);
}

.message-time {
  font-size: 0.75rem;
  color: #64748b;
}

.message-content {
  color: #374151;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-line;
  overflow-wrap: anywhere;
}

/* Responsive Design */
@media (max-width: 768px) {
  .conversation-container {
    padding: 1rem;
  }

  .page-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
    padding: 1.5rem;
  }

  .header-content {
    flex-direction: column;
    gap: 1rem;
  }

  .page-title {
    font-size: 2rem;
  }

  .page-subtitle {
    font-size: 1rem;
  }

  .content-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .card-header {
    padding: 1rem 1.5rem;
  }

  :deep(.conversations-card .p-card-content),
  :deep(.messages-card .p-card-content) {
    padding: 1.5rem;
  }

  :deep(.conversations-card .p-card-header),
  :deep(.messages-card .p-card-header) {
    padding: 1rem 1.5rem;
  }

  .messages-content {
    height: 400px;
  }

  .message-bubble {
    max-width: 85%;
  }

  :deep(.modern-table .p-datatable-tbody > tr > td),
  :deep(.modern-table .p-datatable-thead > tr > th) {
    padding: 0.75rem 0.5rem;
    font-size: 0.875rem;
  }
}

@media (max-width: 480px) {
  .conversation-container {
    padding: 0.5rem;
  }

  .icon-wrapper {
    width: 3rem;
    height: 3rem;
    font-size: 1.5rem;
  }

  .page-title {
    font-size: 1.75rem;
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

  :deep(.conversations-card .p-card-content),
  :deep(.messages-card .p-card-content) {
    padding: 1rem;
  }

  :deep(.conversations-card .p-card-header),
  :deep(.messages-card .p-card-header) {
    padding: 1rem;
  }

  .message-item {
    gap: 0.75rem;
  }

  .message-avatar {
    width: 2rem;
    height: 2rem;
    font-size: 0.875rem;
  }

  .message-bubble {
    padding: 0.75rem;
    max-width: 90%;
  }
}
</style>
