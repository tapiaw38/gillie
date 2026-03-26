<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import Toast from 'primevue/toast'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ToolCallEvent {
  name: string
  arg: string
  done: boolean
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls: ToolCallEvent[]
  shellOutput: string[]
  audioUrl?: string
  isStreaming?: boolean
}

interface ApprovalRequest {
  request_id: string
  tool_name: string
  diff: string
}

// ── Props & Emits ─────────────────────────────────────────────────────────────

interface HistoricalMessage {
  id: string
  content: string
  sender: 'user' | 'assistant'
  created_at: string
  audio_url?: string
}

interface Props {
  conversationId: string | null
  apiKey: string
  initialMessages?: HistoricalMessage[]
}

interface Emits {
  (event: 'messageSent'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// ── State ─────────────────────────────────────────────────────────────────────

const toast = useToast()
const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const isStreaming = ref(false)
const messagesEl = ref<HTMLElement | null>(null)
const textareaEl = ref<HTMLTextAreaElement | null>(null)

const expandedShell = ref<Set<string>>(new Set())
const pendingApproval = ref<ApprovalRequest | null>(null)
const approvalVisible = ref(false)
const approvalFeedback = ref('')
const approvalLoading = ref(false)

// ── Constants ─────────────────────────────────────────────────────────────────

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const TOOL_ICONS: Record<string, string> = {
  read_file: 'pi-file',
  write_file: 'pi-file-edit',
  delete_file: 'pi-trash',
  list_files: 'pi-folder-open',
  run_shell: 'pi-code',
  search: 'pi-search',
  web_search: 'pi-globe',
  http_request: 'pi-send',
}

// ── Markdown renderer ─────────────────────────────────────────────────────────

marked.setOptions({ breaks: true, gfm: true } as object)

// Open all links in system browser (prevents Electron from navigating away)
// marked v12 calls link renderer with positional args: (href, title, text)
marked.use({
  renderer: {
    link(href: string, title: string | null | undefined, text: string) {
      const titleAttr = title ? ` title="${title}"` : ''
      return `<a href="${href}" target="_blank" rel="noopener noreferrer"${titleAttr}>${text}</a>`
    },
  },
})

const renderMarkdown = (content: string): string => {
  const raw = marked.parse(content) as string
  return DOMPurify.sanitize(raw, {
    ADD_TAGS: ['pre', 'code'],
    ADD_ATTR: ['class', 'target', 'rel'],
  })
}

// ── Computed ──────────────────────────────────────────────────────────────────

const canSend = computed(() => inputText.value.trim().length > 0 && !isStreaming.value && props.conversationId !== null)

const lastAssistantMessage = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].role === 'assistant') return messages.value[i]
  }
  return null
})

const isWaitingFirstToken = computed(() => {
  if (!isStreaming.value) return false
  const last = lastAssistantMessage.value
  return last?.isStreaming === true && last.content === ''
})

// ── Scroll ────────────────────────────────────────────────────────────────────

const scrollToBottom = async () => {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

// ── Tool icon helper ──────────────────────────────────────────────────────────

const getToolIcon = (toolName: string): string => {
  const key = Object.keys(TOOL_ICONS).find((k) => toolName.toLowerCase().includes(k))
  return key ? TOOL_ICONS[key] : 'pi-cog'
}

// ── Shell toggle ──────────────────────────────────────────────────────────────

const toggleShell = (messageId: string) => {
  if (expandedShell.value.has(messageId)) {
    expandedShell.value.delete(messageId)
  } else {
    expandedShell.value.add(messageId)
  }
}

const isShellExpanded = (messageId: string) => expandedShell.value.has(messageId)

// ── Streaming send ─────────────────────────────────────────────────────────────

const sendMessage = async () => {
  if (!canSend.value) return

  const content = inputText.value.trim()
  inputText.value = ''

  // Push user message
  messages.value.push({
    id: crypto.randomUUID(),
    role: 'user',
    content,
    toolCalls: [],
    shellOutput: [],
  })

  // Push empty assistant placeholder
  const assistantId = crypto.randomUUID()
  messages.value.push({
    id: assistantId,
    role: 'assistant',
    content: '',
    toolCalls: [],
    shellOutput: [],
    isStreaming: true,
  })

  await scrollToBottom()
  isStreaming.value = true
  emit('messageSent')

  const assistantMsg = messages.value.find((m) => m.id === assistantId)!

  try {
    const response = await fetch(
      `${BASE_URL}/conversation/${props.conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': props.apiKey,
        },
        body: JSON.stringify({ content }),
      },
    )

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    if (!response.body) {
      throw new Error('Response body is empty')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const rawData = line.slice(6).trim()
        if (!rawData) continue

        let payload: unknown
        try {
          payload = JSON.parse(rawData)
        } catch {
          // If JSON.parse fails, treat rawData as a plain string
          payload = rawData
        }

        await processStreamEvent(assistantMsg, payload)
        await scrollToBottom()
      }
    }

    // Flush remaining buffer
    if (buffer.startsWith('data: ')) {
      const rawData = buffer.slice(6).trim()
      if (rawData) {
        let payload: unknown
        try {
          payload = JSON.parse(rawData)
        } catch {
          payload = rawData
        }
        await processStreamEvent(assistantMsg, payload)
      }
    }
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : 'Error desconocido'
    toast.add({
      severity: 'error',
      summary: 'Error de conexión',
      detail: errMsg,
      life: 5000,
    })
    assistantMsg.content = `Error: ${errMsg}`
  } finally {
    assistantMsg.isStreaming = false
    isStreaming.value = false
    await scrollToBottom()
  }
}

const processStreamEvent = async (msg: ChatMessage, payload: unknown) => {
  // Plain string token
  if (typeof payload === 'string') {
    if (payload === '[DONE]') {
      msg.isStreaming = false
      return
    }
    if (payload.startsWith('[ERROR]')) {
      const errText = payload.slice(7).trim()
      toast.add({ severity: 'error', summary: 'Error del stream', detail: errText, life: 5000 })
      msg.content += `\n\n*Error: ${errText}*`
      return
    }
    msg.content += payload
    return
  }

  if (typeof payload !== 'object' || payload === null) return

  const event = payload as Record<string, unknown>

  switch (event.type) {
    case 'tool_call': {
      msg.toolCalls.push({
        name: String(event.name ?? ''),
        arg: String(event.arg ?? ''),
        done: false,
      })
      break
    }

    case 'tool_result': {
      // Mark the most recent undone tool call as done
      const pending = [...msg.toolCalls].reverse().find((t) => !t.done)
      if (pending) pending.done = true
      break
    }

    case 'shell_output': {
      msg.shellOutput.push(String(event.line ?? ''))
      // Auto-expand on first line
      if (msg.shellOutput.length === 1) {
        expandedShell.value.add(msg.id)
      }
      break
    }

    case 'approval_request': {
      pendingApproval.value = {
        request_id: String(event.request_id ?? ''),
        tool_name: String(event.tool_name ?? ''),
        diff: String(event.diff ?? ''),
      }
      approvalFeedback.value = ''
      approvalVisible.value = true
      break
    }

    case 'audio': {
      msg.audioUrl = String(event.url ?? '')
      break
    }

    case 'compaction': {
      toast.add({
        severity: 'info',
        summary: 'Contexto compactado',
        detail: 'La conversación fue compactada para ahorrar tokens.',
        life: 4000,
      })
      break
    }

    default:
      break
  }
}

// ── Approval ──────────────────────────────────────────────────────────────────

const handleApproval = async (approved: boolean) => {
  if (!pendingApproval.value) return
  approvalLoading.value = true

  try {
    await fetch(`${BASE_URL}/conversation/tool/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': props.apiKey,
      },
      body: JSON.stringify({
        request_id: pendingApproval.value.request_id,
        approved,
        feedback: approvalFeedback.value,
      }),
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo enviar la respuesta de aprobación',
      life: 4000,
    })
  } finally {
    approvalLoading.value = false
    approvalVisible.value = false
    pendingApproval.value = null
    approvalFeedback.value = ''
  }
}

// ── Keyboard handler ──────────────────────────────────────────────────────────

const handleKeydown = (e: KeyboardEvent) => {
  if ((e.key === 'Enter' && !e.shiftKey) || (e.key === 'Enter' && e.ctrlKey)) {
    e.preventDefault()
    sendMessage()
  }
}

// ── Diff parser ───────────────────────────────────────────────────────────────

const parseDiffLines = (diff: string) => {
  return diff.split('\n').map((line) => {
    if (line.startsWith('+') && !line.startsWith('+++')) return { text: line, type: 'added' }
    if (line.startsWith('-') && !line.startsWith('---')) return { text: line, type: 'removed' }
    return { text: line, type: 'context' }
  })
}

// ── Watch ─────────────────────────────────────────────────────────────────────

const mapHistoricalMessages = (historical: HistoricalMessage[]): ChatMessage[] =>
  historical.map((m) => ({
    id: m.id,
    role: m.sender,
    content: m.content,
    toolCalls: [],
    shellOutput: [],
    audioUrl: m.audio_url,
  }))

watch(
  () => props.conversationId,
  () => {
    isStreaming.value = false
    messages.value = props.initialMessages ? mapHistoricalMessages(props.initialMessages) : []
    scrollToBottom()
  },
)

// Load historical messages when they arrive from the store (after switchConversation fetches them)
watch(
  () => props.initialMessages,
  (incoming) => {
    if (!isStreaming.value && incoming) {
      messages.value = mapHistoricalMessages(incoming)
      scrollToBottom()
    }
  },
)
</script>

<template>
  <div class="chat-root">
    <Toast />

    <!-- Empty state: no conversation selected -->
    <div v-if="!conversationId" class="chat-empty-state">
      <i class="pi pi-comments chat-empty-icon" />
      <h3 class="chat-empty-title">Selecciona o crea una conversación</h3>
      <p class="chat-empty-subtitle">Elige una conversación del panel izquierdo o crea una nueva para comenzar.</p>
    </div>

    <!-- Chat UI -->
    <template v-else>
      <!-- Messages area -->
      <div ref="messagesEl" class="chat-messages">
        <!-- Empty conversation -->
        <div v-if="messages.length === 0 && !isStreaming" class="chat-placeholder">
          <i class="pi pi-sparkles chat-placeholder-icon" />
          <p class="chat-placeholder-text">Escribe un mensaje para comenzar la conversación</p>
        </div>

        <!-- Message list -->
        <div
          v-for="msg in messages"
          :key="msg.id"
          :class="['msg-row', msg.role === 'user' ? 'msg-row--user' : 'msg-row--assistant']"
        >
          <!-- Avatar -->
          <div :class="['msg-avatar', msg.role === 'user' ? 'msg-avatar--user' : 'msg-avatar--assistant']">
            <i :class="['pi', msg.role === 'user' ? 'pi-user' : 'pi-android']" />
          </div>

          <!-- Bubble -->
          <div :class="['msg-bubble', msg.role === 'user' ? 'msg-bubble--user' : 'msg-bubble--assistant']">

            <!-- Tool call chips -->
            <div v-if="msg.toolCalls.length > 0" class="tool-chips">
              <div
                v-for="(tool, idx) in msg.toolCalls"
                :key="idx"
                :class="['tool-chip', tool.done ? 'tool-chip--done' : 'tool-chip--pending']"
              >
                <i :class="['pi', getToolIcon(tool.name), 'tool-chip-icon']" />
                <span class="tool-chip-name">{{ tool.name }}</span>
                <span v-if="tool.arg" class="tool-chip-arg">{{ tool.arg }}</span>
                <i v-if="tool.done" class="pi pi-check tool-chip-status" />
                <span v-else class="tool-chip-spinner" />
              </div>
            </div>

            <!-- Shell output -->
            <div v-if="msg.shellOutput.length > 0" class="shell-block">
              <button class="shell-toggle" @click="toggleShell(msg.id)">
                <i class="pi pi-terminal shell-toggle-icon" />
                <span>Terminal output ({{ msg.shellOutput.length }} líneas)</span>
                <i :class="['pi', isShellExpanded(msg.id) ? 'pi-chevron-up' : 'pi-chevron-down', 'shell-toggle-chevron']" />
              </button>
              <div v-if="isShellExpanded(msg.id)" class="shell-output">
                <div v-for="(line, i) in msg.shellOutput" :key="i" class="shell-line">{{ line }}</div>
              </div>
            </div>

            <!-- Thinking indicator -->
            <div v-if="msg.isStreaming && msg.content === '' && msg.toolCalls.filter(t => !t.done).length === 0" class="thinking-indicator">
              <span class="thinking-dot" />
              <span class="thinking-dot" />
              <span class="thinking-dot" />
              <span class="thinking-label">pensando...</span>
            </div>

            <!-- Content: markdown for assistant messages -->
            <div
              v-if="msg.content && msg.role === 'assistant'"
              class="msg-content msg-content--markdown"
              v-html="renderMarkdown(msg.content)"
            />
            <!-- Content: plain text for user messages -->
            <div v-else-if="msg.content" class="msg-content">{{ msg.content }}</div>

            <!-- Audio player -->
            <div v-if="msg.audioUrl" class="msg-audio">
              <audio :src="msg.audioUrl" controls class="msg-audio-player" />
            </div>

            <!-- Streaming cursor -->
            <span v-if="msg.isStreaming && msg.content !== ''" class="stream-cursor" />
          </div>
        </div>
      </div>

      <!-- Input area -->
      <div class="chat-input-area">
        <div class="chat-input-wrapper">
          <Textarea
            ref="textareaEl"
            v-model="inputText"
            placeholder="Escribe un mensaje... (Enter para enviar, Shift+Enter para nueva línea)"
            :disabled="isStreaming || !conversationId"
            :rows="1"
            auto-resize
            class="chat-textarea"
            @keydown="handleKeydown"
          />
          <Button
            icon="pi pi-send"
            :disabled="!canSend"
            :loading="isStreaming && isWaitingFirstToken"
            severity="info"
            class="chat-send-btn"
            @click="sendMessage"
            aria-label="Enviar mensaje"
          />
        </div>
        <p class="chat-input-hint">
          Enter para enviar &middot; Shift+Enter para nueva línea
        </p>
      </div>
    </template>

    <!-- Tool approval dialog -->
    <Dialog
      v-model:visible="approvalVisible"
      :closable="false"
      :draggable="false"
      :modal="true"
      header="Aprobación requerida"
      class="approval-dialog"
      style="width: min(680px, 95vw)"
    >
      <div class="approval-body">
        <div class="approval-warning">
          <i class="pi pi-exclamation-triangle approval-warning-icon" />
          <div>
            <p class="approval-warning-title">El asistente solicita ejecutar una acción</p>
            <p class="approval-warning-tool">
              Herramienta: <strong>{{ pendingApproval?.tool_name }}</strong>
            </p>
          </div>
        </div>

        <div v-if="pendingApproval?.diff" class="diff-viewer">
          <p class="diff-label">Cambios propuestos:</p>
          <div class="diff-content">
            <div
              v-for="(line, i) in parseDiffLines(pendingApproval.diff)"
              :key="i"
              :class="['diff-line', `diff-line--${line.type}`]"
            >{{ line.text }}</div>
          </div>
        </div>

        <div class="approval-feedback">
          <label class="approval-feedback-label">Comentario (opcional):</label>
          <Textarea
            v-model="approvalFeedback"
            placeholder="Añade un comentario para el asistente..."
            :rows="2"
            auto-resize
            class="approval-feedback-input"
          />
        </div>
      </div>

      <template #footer>
        <div class="approval-footer">
          <Button
            label="Rechazar"
            icon="pi pi-times"
            severity="danger"
            outlined
            :loading="approvalLoading"
            @click="handleApproval(false)"
          />
          <Button
            label="Aprobar"
            icon="pi pi-check"
            severity="success"
            :loading="approvalLoading"
            @click="handleApproval(true)"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
/* ── Root ─────────────────────────────────────────────────────────────── */
.chat-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--do-bg);
  position: relative;
}

/* ── Empty / placeholder states ───────────────────────────────────────── */
.chat-empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
  text-align: center;
}

.chat-empty-icon {
  font-size: 3rem;
  color: var(--do-text-muted);
  opacity: 0.5;
}

.chat-empty-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--do-text-secondary);
  margin: 0;
}

.chat-empty-subtitle {
  font-size: 0.875rem;
  color: var(--do-text-muted);
  max-width: 340px;
  margin: 0;
  line-height: 1.5;
}

.chat-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  height: 100%;
  padding: 2rem;
  text-align: center;
}

.chat-placeholder-icon {
  font-size: 2rem;
  color: var(--do-text-muted);
  opacity: 0.4;
}

.chat-placeholder-text {
  font-size: 0.875rem;
  color: var(--do-text-muted);
  margin: 0;
}

/* ── Messages area ────────────────────────────────────────────────────── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem 1rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  scroll-behavior: smooth;
}

.chat-messages::-webkit-scrollbar {
  width: 4px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

/* ── Message rows ─────────────────────────────────────────────────────── */
.msg-row {
  display: flex;
  gap: 0.625rem;
  align-items: flex-start;
  max-width: 100%;
}

.msg-row--user {
  flex-direction: row-reverse;
  align-self: flex-end;
  max-width: 75%;
}

.msg-row--assistant {
  flex-direction: row;
  align-self: flex-start;
  max-width: 80%;
}

/* ── Avatars ──────────────────────────────────────────────────────────── */
.msg-avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.msg-avatar--user {
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.35);
  color: var(--do-blue);
}

.msg-avatar--assistant {
  background: rgba(10, 207, 131, 0.15);
  border: 1px solid rgba(10, 207, 131, 0.3);
  color: var(--do-success);
}

/* ── Bubbles ──────────────────────────────────────────────────────────── */
.msg-bubble {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  min-width: 0;
  word-break: break-word;
}

.msg-bubble--user {
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-top-right-radius: 0.2rem;
}

.msg-bubble--assistant {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-top-left-radius: 0.2rem;
}

/* ── Message content ──────────────────────────────────────────────────── */
.msg-content {
  font-size: 0.9rem;
  line-height: 1.65;
  color: var(--do-text);
  white-space: pre-wrap;
}

.msg-content--markdown {
  white-space: normal;
}

/* Markdown rendered content */
.msg-content--markdown :deep(p) {
  margin: 0 0 0.5em;
}

.msg-content--markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.msg-content--markdown :deep(h1),
.msg-content--markdown :deep(h2),
.msg-content--markdown :deep(h3),
.msg-content--markdown :deep(h4) {
  margin: 0.75em 0 0.25em;
  font-weight: 600;
  color: var(--do-text);
}

.msg-content--markdown :deep(ul),
.msg-content--markdown :deep(ol) {
  margin: 0.25em 0 0.5em 1.25em;
  padding: 0;
}

.msg-content--markdown :deep(li) {
  list-style: disc !important;
  margin-bottom: 0.2em;
}

.msg-content--markdown :deep(ol li) {
  list-style: decimal !important;
}

.msg-content--markdown :deep(code) {
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 0.82em;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.3rem;
  padding: 0.1em 0.35em;
  color: #7dd3fc;
}

.msg-content--markdown :deep(pre) {
  background: rgba(0, 0, 0, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0.5rem;
  padding: 0.875rem 1rem;
  overflow-x: auto;
  margin: 0.5em 0;
}

.msg-content--markdown :deep(pre code) {
  background: none;
  border: none;
  padding: 0;
  font-size: 0.85em;
  color: #e2e8f0;
}

.msg-content--markdown :deep(blockquote) {
  border-left: 3px solid var(--do-blue);
  margin: 0.5em 0;
  padding: 0.25em 0.75em;
  color: var(--do-text-secondary);
  font-style: italic;
}

.msg-content--markdown :deep(a) {
  color: var(--do-blue);
  text-decoration: underline !important;
}

.msg-content--markdown :deep(hr) {
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin: 0.75em 0;
}

.msg-content--markdown :deep(table) {
  border-collapse: collapse;
  width: 100%;
  font-size: 0.875em;
  margin: 0.5em 0;
}

.msg-content--markdown :deep(th),
.msg-content--markdown :deep(td) {
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0.35em 0.6em;
  text-align: left;
}

.msg-content--markdown :deep(th) {
  background: rgba(255, 255, 255, 0.05);
  font-weight: 600;
}

/* ── Streaming cursor ─────────────────────────────────────────────────── */
.stream-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: var(--do-blue);
  margin-left: 1px;
  vertical-align: text-bottom;
  animation: blink 0.9s step-start infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ── Thinking indicator ───────────────────────────────────────────────── */
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0;
}

.thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--do-text-muted);
  animation: thinking-bounce 1.2s ease-in-out infinite;
}

.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes thinking-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-5px); opacity: 1; }
}

.thinking-label {
  font-size: 0.8rem;
  color: var(--do-text-muted);
  margin-left: 0.25rem;
  font-style: italic;
}

/* ── Tool chips ───────────────────────────────────────────────────────── */
.tool-chips {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.tool-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem;
  border-radius: 1rem;
  font-size: 0.78rem;
  font-weight: 500;
  width: fit-content;
  max-width: 100%;
}

.tool-chip--pending {
  background: rgba(245, 166, 35, 0.1);
  border: 1px solid rgba(245, 166, 35, 0.25);
  color: var(--do-warning);
}

.tool-chip--done {
  background: rgba(10, 207, 131, 0.08);
  border: 1px solid rgba(10, 207, 131, 0.2);
  color: var(--do-success);
}

.tool-chip-icon {
  font-size: 0.75rem;
  flex-shrink: 0;
}

.tool-chip-name {
  font-family: monospace;
  font-size: 0.8rem;
}

.tool-chip-arg {
  color: inherit;
  opacity: 0.7;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
  font-style: italic;
}

.tool-chip-status {
  font-size: 0.7rem;
  flex-shrink: 0;
}

.tool-chip-spinner {
  width: 10px;
  height: 10px;
  border: 1.5px solid rgba(245, 166, 35, 0.3);
  border-top-color: var(--do-warning);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Shell block ──────────────────────────────────────────────────────── */
.shell-block {
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.07);
}

.shell-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.4rem 0.75rem;
  background: rgba(0, 0, 0, 0.35);
  border: none;
  cursor: pointer;
  color: var(--do-text-secondary);
  font-size: 0.8rem;
  font-family: inherit;
  text-align: left;
  transition: background 0.15s;
}

.shell-toggle:hover {
  background: rgba(0, 0, 0, 0.5);
}

.shell-toggle-icon {
  font-size: 0.8rem;
  color: var(--do-success);
}

.shell-toggle-chevron {
  margin-left: auto;
  font-size: 0.7rem;
}

.shell-output {
  background: #0a0f1a;
  padding: 0.625rem 0.875rem;
  max-height: 280px;
  overflow-y: auto;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.shell-line {
  font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace;
  font-size: 0.8rem;
  color: #a3e635;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.55;
}

/* ── Audio player ─────────────────────────────────────────────────────── */
.msg-audio-player {
  width: 100%;
  max-width: 320px;
  height: 36px;
  border-radius: 0.5rem;
}

/* ── Input area ───────────────────────────────────────────────────────── */
.chat-input-area {
  flex-shrink: 0;
  padding: 0.875rem 1rem 0.625rem;
  background: rgba(6, 13, 26, 0.95);
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(12px);
}

.chat-input-wrapper {
  display: flex;
  gap: 0.5rem;
  align-items: flex-end;
}

.chat-textarea {
  flex: 1;
  min-height: 2.5rem;
  max-height: 12rem;
  resize: none;
  border-radius: 0.625rem;
  font-size: 0.9rem;
  line-height: 1.5;
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1.5px solid rgba(255, 255, 255, 0.1) !important;
  color: var(--do-text) !important;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.chat-textarea:focus {
  border-color: var(--do-blue) !important;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15) !important;
  outline: none;
}

.chat-send-btn {
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.625rem;
}

.chat-input-hint {
  font-size: 0.72rem;
  color: var(--do-text-muted);
  margin: 0.35rem 0 0;
  text-align: right;
}

/* ── Approval dialog ──────────────────────────────────────────────────── */
.approval-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.approval-warning {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.875rem;
  background: rgba(245, 166, 35, 0.08);
  border: 1px solid rgba(245, 166, 35, 0.25);
  border-radius: 0.5rem;
}

.approval-warning-icon {
  font-size: 1.5rem;
  color: var(--do-warning);
  flex-shrink: 0;
  margin-top: 0.1rem;
}

.approval-warning-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--do-text);
  margin: 0 0 0.25rem;
}

.approval-warning-tool {
  font-size: 0.85rem;
  color: var(--do-text-secondary);
  margin: 0;
}

.diff-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--do-text-secondary);
  margin: 0 0 0.5rem;
}

.diff-viewer {
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.diff-content {
  background: #0a0f1a;
  padding: 0.625rem 0.875rem;
  max-height: 240px;
  overflow-y: auto;
}

.diff-line {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.8rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.diff-line--added {
  color: #4ade80;
  background: rgba(74, 222, 128, 0.06);
}

.diff-line--removed {
  color: #f87171;
  background: rgba(248, 113, 113, 0.06);
}

.diff-line--context {
  color: var(--do-text-muted);
}

.approval-feedback-label {
  display: block;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--do-text-secondary);
  margin-bottom: 0.375rem;
}

.approval-feedback-input {
  width: 100%;
  font-size: 0.875rem;
}

.approval-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

/* ── Responsive ───────────────────────────────────────────────────────── */
@media (max-width: 640px) {
  .msg-row--user,
  .msg-row--assistant {
    max-width: 92%;
  }

  .chat-messages {
    padding: 1rem 0.75rem 0.5rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .stream-cursor,
  .thinking-dot,
  .tool-chip-spinner {
    animation: none;
  }
}
</style>
