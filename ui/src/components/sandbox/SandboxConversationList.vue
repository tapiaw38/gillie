<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import Badge from 'primevue/badge'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import { useDateFormat } from '@/composables/useDateFormat'
import type { SandboxConversation } from '@/types/sandbox'

interface Props {
  conversations: SandboxConversation[]
  currentConversationId: string | null
  isLoading?: boolean
  error?: string | null
}

interface Emits {
  (event: 'select', conversationId: string): void
  (event: 'create'): void
  (event: 'delete', conversationId: string): void
}

const props = withDefaults(defineProps<Props>(), {
  isLoading: false,
  error: null,
})

const emit = defineEmits<Emits>()
const { dateFormat } = useDateFormat()

const handleSelect = (conversationId: string) => {
  emit('select', conversationId)
}

const handleCreate = () => {
  emit('create')
}

const handleDelete = (conversationId: string, event: Event) => {
  event.stopPropagation()
  emit('delete', conversationId)
}

const isCurrentConversation = (conversationId: string) => {
  return conversationId === props.currentConversationId
}

const getConversationTitle = (conversation: SandboxConversation) => {
  return conversation.title || 'Conversación Sin Título'
}

const getMessageCount = (conversation: SandboxConversation) => {
  return conversation.message_count || 0
}
</script>

<template>
  <div class="sandbox-conversation-list">
    <div class="list-header mb-3">
      <h3 class="m-0 text-lg font-semibold">Conversaciones</h3>
      <Button
        label="Nueva"
        icon="pi pi-plus"
        @click="handleCreate"
        class="p-button-sm"
        severity="info"
      />
    </div>

    <Message v-if="error" severity="error" :closable="false" class="mb-3">
      {{ error }}
    </Message>

    <div v-if="isLoading && conversations.length === 0" class="loading-state">
      <ProgressSpinner style="width: 50px; height: 50px" strokeWidth="4" />
      <p class="text-sm text-color-secondary">Cargando conversaciones...</p>
    </div>

    <div v-else-if="conversations.length === 0" class="empty-state">
      <i class="pi pi-inbox text-4xl text-color-secondary mb-2"></i>
      <p class="text-sm text-color-secondary">No hay conversaciones aún</p>
      <Button
        label="Nueva conversación"
        icon="pi pi-plus"
        @click="handleCreate"
        class="p-button-sm"
        severity="info"
      />
    </div>

    <div v-else class="conversation-items">
      <Card
        v-for="conversation in conversations"
        :key="conversation.id"
        :class="['conversation-card', { active: isCurrentConversation(conversation.id) }]"
        @click="handleSelect(conversation.id)"
      >
        <template #content>
          <div class="conversation-content">
            <div class="conversation-header">
              <div class="flex align-items-center gap-2 flex-1">
                <i class="pi pi-comments text-blue-500"></i>
                <h4 class="m-0 text-base font-semibold">
                  {{ getConversationTitle(conversation) }}
                </h4>
              </div>
              <Button
                icon="pi pi-trash"
                @click="handleDelete(conversation.id, $event)"
                class="p-button-rounded p-button-text p-button-sm p-button-danger"
                v-tooltip.left="'Eliminar conversación'"
              />
            </div>

            <div class="conversation-meta mt-2">
              <div class="flex align-items-center gap-2">
                <Badge :value="getMessageCount(conversation)" severity="info" />
                <span class="text-xs text-color-secondary">mensajes</span>
              </div>
              <span class="text-xs text-color-secondary">
                {{ dateFormat(conversation.updated_at) }}
              </span>
            </div>

          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.sandbox-conversation-list {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(255,255,255,0.04);
  padding: 1rem;
}

.list-header {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.list-header h3 {
  color: var(--vt-c-gray-800);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  text-align: center;
  gap: 0.5rem;
}

.conversation-items {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow-y: auto;
  flex: 1;
}

.conversation-card {
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  background: var(--surface-card);
}

.conversation-card:hover {
  transform: translateX(4px);
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.15);
}

.conversation-card.active {
  background: linear-gradient(135deg, var(--vt-c-info-light) 0%, var(--vt-c-info-lighter) 100%);
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.2);
}

:deep(.conversation-card .p-card-content) {
  padding: 1rem;
}

.conversation-content {
  width: 100%;
}

.conversation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.conversation-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sandbox-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: var(--vt-c-info-lighter);
  border-radius: 4px;
  color: var(--vt-c-info-dark);
}

.text-lg {
  font-size: 1.125rem;
}

.text-base {
  font-size: 1rem;
}

.text-xs {
  font-size: 0.75rem;
}

.text-sm {
  font-size: 0.875rem;
}

.text-4xl {
  font-size: 2.25rem;
}

.text-blue-500 {
  color: var(--vt-c-info);
}
</style>
