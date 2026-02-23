<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import ScrollPanel from 'primevue/scrollpanel'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Badge from 'primevue/badge'
import { useDateFormat } from '@/composables/useDateFormat'
import type { SandboxMessage, SandboxConversation } from '@/types/sandbox'

interface Props {
  messages: SandboxMessage[]
  currentConversation: SandboxConversation | undefined
  isSending?: boolean
  isLoading?: boolean
  error?: string | null
}

interface Emits {
  (event: 'send', content: string): void
}

const props = withDefaults(defineProps<Props>(), {
  isSending: false,
  isLoading: false,
  error: null,
})

const emit = defineEmits<Emits>()
const { dateFormat } = useDateFormat()

const messageInput = ref('')
const messagesContainer = ref<InstanceType<typeof ScrollPanel> | null>(null)

const canSendMessage = computed(() => {
  return messageInput.value.trim().length > 0 && !props.isSending
})

const handleSend = async () => {
  if (canSendMessage.value) {
    emit('send', messageInput.value.trim())
    messageInput.value = ''
    await nextTick()
    await scrollToBottom()
  }
}

const handleKeyPress = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    const el = (messagesContainer.value as unknown as { $el: HTMLElement }).$el
    const scrollContent = el?.querySelector('.p-scrollpanel-content')
    if (scrollContent) {
      scrollContent.scrollTop = scrollContent.scrollHeight
    }
  }
}

watch(
  () => props.messages,
  async () => {
    await nextTick()
    await scrollToBottom()
  },
  { deep: true, immediate: false },
)

watch(
  () => props.isSending,
  async (newValue, oldValue) => {
    if (oldValue && !newValue) {
      await nextTick()
      await scrollToBottom()
    }
  },
)

const getMessageTime = (dateString: string) => {
  return dateFormat(dateString)
}
</script>

<template>
  <div class="sandbox-chat">
    <!-- Chat Header -->
    <div class="chat-header">
      <div class="flex align-items-center gap-2">
        <i class="pi pi-shield text-blue-500 text-2xl"></i>
        <div>
          <h3 class="m-0 text-lg font-semibold">
            {{ currentConversation?.title || 'Chat de Pruebas' }}
          </h3>
          <div class="flex align-items-center gap-2 mt-1">
            <Badge value="Modo Sandbox" severity="info" />
            <span class="text-xs text-color-secondary">
              {{ messages.length }} mensaje{{ messages.length !== 1 ? 's' : '' }}
            </span>
          </div>
        </div>
      </div>

      <div class="conversation-info">
        <div class="info-item">
          <i class="pi pi-check-circle text-xs"></i>
          <span class="text-xs">Pruebas</span>
        </div>
        <div class="info-item">
          <i class="pi pi-comments text-xs"></i>
          <span class="text-xs"
            >{{ messages.length }} mensaje{{ messages.length !== 1 ? 's' : '' }}</span
          >
        </div>
      </div>
    </div>

    <!-- Error Message -->
    <Message v-if="error" severity="error" :closable="false" class="m-3">
      {{ error }}
    </Message>

    <!-- Messages Area -->
    <ScrollPanel ref="messagesContainer" class="messages-container" style="height: 100%">
      <!-- Loading State -->
      <div v-if="isLoading && messages.length === 0" class="loading-state">
        <ProgressSpinner style="width: 50px; height: 50px" strokeWidth="4" />
        <p class="text-sm text-color-secondary">Cargando conversación...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="messages.length === 0" class="empty-state">
        <i class="pi pi-comments text-6xl text-blue-300 mb-3"></i>
        <h4 class="m-0 mb-2">Inicia una Conversación de Prueba</h4>
        <p class="text-sm text-color-secondary mb-0">
          Envía un mensaje para probar tu asistente de IA en un entorno seguro
        </p>
      </div>

      <!-- Messages -->
      <div v-else class="messages-list">
        <div
          v-for="message in messages"
          :key="message.id"
          :class="['message-wrapper', message.sender]"
        >
          <Card :class="['message-card', message.sender]">
            <template #content>
              <div class="message-header">
                <span class="message-sender">
                  <i
                    :class="['pi', message.sender === 'user' ? 'pi-user' : 'pi-android', 'mr-1']"
                  ></i>
                  {{ message.sender === 'user' ? 'Tú' : 'Asistente' }}
                </span>
                <span class="message-time text-xs">
                  {{ getMessageTime(message.created_at) }}
                </span>
              </div>
              <div class="message-content">
                {{ message.content }}
              </div>
            </template>
          </Card>
        </div>

        <!-- Sending Indicator -->
        <div v-if="isSending" class="message-wrapper assistant">
          <Card class="message-card assistant">
            <template #content>
              <div class="flex align-items-center gap-2">
                <ProgressSpinner style="width: 20px; height: 20px" strokeWidth="4" />
                <span class="text-sm">El asistente está escribiendo...</span>
              </div>
            </template>
          </Card>
        </div>
      </div>
    </ScrollPanel>

    <!-- Input Area -->
    <div class="chat-input">
      <div class="input-container">
        <InputText
          v-model="messageInput"
          placeholder="Escribe tu mensaje..."
          @keypress="handleKeyPress"
          :disabled="isSending"
          class="message-input"
        />
        <Button
          icon="pi pi-send"
          @click="handleSend"
          :disabled="!canSendMessage"
          :loading="isSending"
          severity="info"
          class="send-button"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.sandbox-chat {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--surface-ground);
}

.chat-header {
  padding: 1.5rem;
  background: linear-gradient(135deg, var(--vt-c-info-light) 0%, var(--vt-c-info-lighter) 100%);
  border-bottom: 2px solid var(--vt-c-info);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.chat-header h3 {
  color: var(--vt-c-gray-800);
}

.conversation-info {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: var(--vt-c-white);
  border-radius: 4px;
  border: 1px solid var(--vt-c-info);
}

.info-item i {
  color: var(--vt-c-info-dark);
}

.info-item span {
  color: var(--vt-c-gray-700);
  font-weight: 600;
}

.messages-container {
  flex: 1;
  background: var(--surface-card);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
  text-align: center;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.5rem;
  padding-bottom: 25rem;
}

.message-wrapper {
  display: flex;
  max-width: 70%;
}

.message-wrapper.user {
  align-self: flex-end;
  margin-left: auto;
}

.message-wrapper.assistant {
  align-self: flex-start;
  margin-right: auto;
}

.message-card {
  width: 100%;
}

.message-card.user {
  background: linear-gradient(135deg, var(--vt-c-info-light) 0%, var(--vt-c-info-lighter) 100%);
  border-left: 4px solid var(--vt-c-info);
}

.message-card.assistant {
  background: linear-gradient(135deg, var(--vt-c-gray-50) 0%, var(--vt-c-gray-100) 100%);
  border-left: 4px solid var(--vt-c-info);
}

:deep(.message-card .p-card-content) {
  padding: 1rem;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.message-sender {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.message-time {
  color: var(--text-color-secondary);
  opacity: 0.7;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
}

.chat-input {
  position: fixed;
  bottom: 0;
  right: 0;
  left: 350px;
  padding: 1rem 1.5rem;
  background: var(--surface-card);
  border-top: 1px solid var(--surface-border);
  z-index: 100;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
}

@media (max-width: 768px) {
  .chat-input {
    left: 0;
  }
}

@media (min-width: 769px) and (max-width: 1024px) {
  .chat-input {
    left: 280px;
  }
}

.input-container {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.message-input {
  flex: 1;
}

.send-button {
  flex-shrink: 0;
}

.text-lg {
  font-size: 1.125rem;
}

.text-sm {
  font-size: 0.875rem;
}

.text-xs {
  font-size: 0.75rem;
}

.text-2xl {
  font-size: 1.5rem;
}

.text-6xl {
  font-size: 3.75rem;
}

.text-blue-300 {
  color: var(--vt-c-info-light);
}

.text-blue-500 {
  color: var(--vt-c-info);
}

.text-blue-600 {
  color: var(--vt-c-info-dark);
}
</style>
