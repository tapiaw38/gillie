<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'
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
  role: 'user' | 'assistant' | 'system'
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
  (event: 'newConversation'): void
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

// Workspace state
const currentWorkspace = ref('')

// Autocomplete state
const autocompleteVisible = ref(false)
const autocompleteItems = ref<{ label: string; value: string; hint?: string }[]>([])
const autocompleteIndex = ref(0)
// Position in inputText where the current @ or / token starts (for replacement on select)
const tokenStart = ref(0)
const tokenIsAt = ref(false) // true = @ token, false = / command

// ── Constants ─────────────────────────────────────────────────────────────────

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const SLASH_COMMANDS = [
  { label: '/new', value: '/new', hint: 'Start a new conversation' },
  { label: '/clear', value: '/clear', hint: 'Clear messages in this view' },
  { label: '/workspace', value: '/workspace ', hint: 'Set or show current workspace path' },
  { label: '/model', value: '/model', hint: 'Show current provider info' },
]

const AT_HINTS = [
  { label: '@file.ext', value: '@', hint: 'Inject a file as context' },
  { label: '@dir/', value: '@', hint: 'List directory contents' },
  { label: '@https://...', value: '@', hint: 'Fetch a URL as context' },
  { label: '@@glob/**', value: '@@', hint: 'Glob-expand a file pattern' },
]

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

const canSend = computed(
  () => inputText.value.trim().length > 0 && !isStreaming.value && props.conversationId !== null,
)

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

// ── System message helper ─────────────────────────────────────────────────────

const addSystemMessage = (content: string) => {
  messages.value.push({
    id: crypto.randomUUID(),
    role: 'system',
    content,
    toolCalls: [],
    shellOutput: [],
  })
  scrollToBottom()
}

// ── Slash command handler ─────────────────────────────────────────────────────

/**
 * Returns true if the input was a slash command (handled client-side).
 */
const handleSlashCommand = (text: string): boolean => {
  const trimmed = text.trim()

  if (trimmed === '/new') {
    emit('newConversation')
    return true
  }

  if (trimmed === '/clear') {
    messages.value = []
    return true
  }

  if (trimmed === '/model') {
    addSystemMessage(
      `Current provider: configured in backend. Use \`/model\` in the CLI to see full provider details (e.g. \`gillie /model\`).`,
    )
    return true
  }

  if (trimmed.startsWith('/workspace')) {
    const arg = trimmed.slice('/workspace'.length).trim()
    if (!arg) {
      const info = currentWorkspace.value
        ? `Current workspace: \`${currentWorkspace.value}\``
        : 'No workspace set. Use `/workspace /path/to/dir` to set one.'
      addSystemMessage(info)
    } else {
      currentWorkspace.value = arg
      addSystemMessage(`Workspace set to: \`${arg}\``)
    }
    return true
  }

  return false
}

// ── @ reference expansion ─────────────────────────────────────────────────────

declare global {
  interface Window {
    electronAPI?: {
      readFile: (filePath: string) => Promise<string>
      listDir: (dirPath: string) => Promise<string[]>
      listDirShallow: (dirPath: string) => Promise<string[]>
      glob: (pattern: string, base: string) => Promise<string[]>
      fetchUrl: (url: string) => Promise<string>
    }
  }
}

/**
 * Expand all @references in the text before sending to the backend.
 * Prepends context blocks and returns the enriched message string.
 */
const expandAtReferences = async (text: string): Promise<string> => {
  const api = window.electronAPI
  if (!api) return text

  // Match patterns: @@glob, @https://..., @file/path or @relative
  const atPattern = /@@([^\s]+)|@(https?:\/\/[^\s]+)|@([^\s@]+)/g
  const contexts: string[] = []
  let match: RegExpExecArray | null

  const promises: Promise<void>[] = []

  // Collect all matches first to run in parallel
  const allMatches: RegExpExecArray[] = []
  while ((match = atPattern.exec(text)) !== null) {
    allMatches.push({ ...match, index: match.index, input: match.input } as RegExpExecArray)
  }

  for (const m of allMatches) {
    const globPattern = m[1] // @@glob
    const urlRef = m[2] // @https://...
    const fileRef = m[3] // @path

    if (globPattern) {
      promises.push(
        api
          .glob(globPattern, currentWorkspace.value || '.')
          .then((files) => {
            if (files.length > 0) {
              contexts.push(`[Files matching @@${globPattern}]\n${files.join('\n')}`)
            } else {
              contexts.push(`[@@${globPattern}: no files matched]`)
            }
          })
          .catch((err: unknown) => {
            contexts.push(
              `[@@${globPattern}: error - ${err instanceof Error ? err.message : String(err)}]`,
            )
          }),
      )
    } else if (urlRef) {
      promises.push(
        api
          .fetchUrl(urlRef)
          .then((content) => {
            contexts.push(`[Context from @${urlRef}]\n${content}`)
          })
          .catch((err: unknown) => {
            contexts.push(
              `[@${urlRef}: fetch error - ${err instanceof Error ? err.message : String(err)}]`,
            )
          }),
      )
    } else if (fileRef) {
      // Directory listing (ends with /) vs file read
      if (fileRef.endsWith('/')) {
        const dirPath = fileRef.startsWith('/')
          ? fileRef
          : `${currentWorkspace.value || '.'}/${fileRef}`
        promises.push(
          api
            .listDir(dirPath)
            .then((files) => {
              contexts.push(`[Directory listing: @${fileRef}]\n${files.join('\n')}`)
            })
            .catch((err: unknown) => {
              contexts.push(
                `[@${fileRef}: listDir error - ${err instanceof Error ? err.message : String(err)}]`,
              )
            }),
        )
      } else {
        const filePath = fileRef.startsWith('/')
          ? fileRef
          : `${currentWorkspace.value || '.'}/${fileRef}`
        promises.push(
          api
            .readFile(filePath)
            .then((content) => {
              contexts.push(`[Context from @${fileRef}]\n${content}`)
            })
            .catch((err: unknown) => {
              contexts.push(
                `[@${fileRef}: read error - ${err instanceof Error ? err.message : String(err)}]`,
              )
            }),
        )
      }
    }
  }

  await Promise.all(promises)

  if (contexts.length === 0) return text

  const contextBlock = contexts.join('\n\n')
  return `${contextBlock}\n\n---\n\n${text}`
}

// ── Streaming send ─────────────────────────────────────────────────────────────

const sendMessage = async () => {
  if (!canSend.value) return

  const rawContent = inputText.value.trim()
  inputText.value = ''
  autocompleteVisible.value = false

  // Handle slash commands client-side
  if (handleSlashCommand(rawContent)) return

  // Expand @ references
  let content: string
  try {
    content = await expandAtReferences(rawContent)
  } catch {
    content = rawContent
  }

  // Push user message (show original text, not the expanded context)
  messages.value.push({
    id: crypto.randomUUID(),
    role: 'user',
    content: rawContent,
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
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'x-api-key': props.apiKey,
    }
    if (currentWorkspace.value) {
      headers['X-Gillie-Workspace'] = currentWorkspace.value
    }

    const response = await fetch(
      `${BASE_URL}/conversation/${props.conversationId}/message/stream`,
      {
        method: 'POST',
        headers,
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
      const pending = [...msg.toolCalls].reverse().find((t) => !t.done)
      if (pending) pending.done = true
      break
    }

    case 'shell_output': {
      msg.shellOutput.push(String(event.line ?? ''))
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
  } catch {
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

// ── Autocomplete ──────────────────────────────────────────────────────────────

/** Get the raw <textarea> element from PrimeVue's wrapper */
const getRawTextarea = (): HTMLTextAreaElement | null => {
  const el = textareaEl.value as HTMLElement | null
  return (el?.querySelector?.('textarea') ?? el) as HTMLTextAreaElement | null
}

/** Find the @ or @@ token that ends at `cursorPos` in `text`. Returns null if none. */
const findAtToken = (
  text: string,
  cursorPos: number,
): { start: number; partial: string } | null => {
  let i = cursorPos - 1
  // Walk back until whitespace
  while (i >= 0 && !/\s/.test(text[i])) i--
  const start = i + 1
  const token = text.slice(start, cursorPos)
  if (token.startsWith('@')) return { start, partial: token }
  return null
}

/** Fetch directory entries for a partial path and return autocomplete items */
const fetchPathCompletions = async (
  partial: string, // e.g. "@/home/ta" or "@rel/pa"
): Promise<{ label: string; value: string; hint: string }[]> => {
  if (!window.electronAPI) return []

  // Strip leading @ / @@
  const isDouble = partial.startsWith('@@')
  const pathPart = partial.slice(isDouble ? 2 : 1) // path after @ or @@

  // Determine dir to list and prefix to filter
  const lastSlash = pathPart.lastIndexOf('/')
  const dirToList = lastSlash >= 0 ? pathPart.slice(0, lastSlash + 1) : ''
  const prefix =
    lastSlash >= 0 ? pathPart.slice(lastSlash + 1).toLowerCase() : pathPart.toLowerCase()

  // Resolve dir: if absolute use as-is, else relative to workspace or cwd
  let absDir: string
  if (dirToList.startsWith('/')) {
    absDir = dirToList
  } else {
    const base = currentWorkspace.value || '/'
    absDir = base.endsWith('/') ? base + dirToList : base + '/' + dirToList
  }

  try {
    // listDirShallow returns entries like "file.txt" or "dir/" (dirs have trailing /)
    const entries = await window.electronAPI!.listDirShallow(absDir)
    const atPrefix = isDouble ? '@@' : '@'
    return entries
      .filter((e) => e.toLowerCase().startsWith(prefix.toLowerCase()))
      .slice(0, 20)
      .map((e) => {
        const isDir = e.endsWith('/')
        const name = isDir ? e.slice(0, -1) : e
        const fullPath = dirToList + name
        return {
          label: e, // "dirname/" or "file.txt"
          value: atPrefix + fullPath + (isDir ? '/' : ''), // "@/full/dir/" or "@/full/file.txt"
          hint: isDir ? 'directorio' : 'archivo',
        }
      })
  } catch {
    return []
  }
}

const updateAutocomplete = async (value: string) => {
  const ta = getRawTextarea()
  const cursor = ta?.selectionStart ?? value.length

  // ── Slash commands (only when input starts with / and has no space before cursor) ──
  const textToCursor = value.slice(0, cursor)
  if (value.startsWith('/') && !value.slice(0, cursor).includes(' ')) {
    const partial = textToCursor.toLowerCase()
    const filtered = SLASH_COMMANDS.filter((c) => c.value.toLowerCase().startsWith(partial))
    autocompleteItems.value = filtered
    autocompleteVisible.value = filtered.length > 0
    autocompleteIndex.value = 0
    tokenStart.value = 0
    tokenIsAt.value = false
    return
  }

  // ── @ references ──
  const atToken = findAtToken(value, cursor)
  if (atToken) {
    tokenStart.value = atToken.start
    tokenIsAt.value = true

    const partial = atToken.partial

    // Static hints when user just typed @ or @@
    if (partial === '@' || partial === '@@') {
      autocompleteItems.value = AT_HINTS
      autocompleteVisible.value = true
      autocompleteIndex.value = 0
      return
    }

    // Skip URL — no completion for http
    if (partial.startsWith('@http')) {
      autocompleteVisible.value = false
      return
    }

    // Filesystem path completion
    const items = await fetchPathCompletions(partial)
    autocompleteItems.value = items
    autocompleteVisible.value = items.length > 0
    autocompleteIndex.value = 0
    return
  }

  autocompleteVisible.value = false
}

const selectAutocompleteItem = (item: { label: string; value: string }) => {
  const ta = getRawTextarea()
  const cursor = ta?.selectionStart ?? inputText.value.length

  if (tokenIsAt.value) {
    // Replace only the @ token portion
    const before = inputText.value.slice(0, tokenStart.value)
    const after = inputText.value.slice(cursor)
    inputText.value = before + item.value + after
    // Place cursor after inserted text
    nextTick(() => {
      const pos = tokenStart.value + item.value.length
      ta?.setSelectionRange(pos, pos)
      ta?.focus()
      // If it ends with / (directory), trigger completion again
      if (item.value.endsWith('/')) updateAutocomplete(inputText.value)
    })
  } else {
    // Slash command — replace whole input
    inputText.value = item.value
    autocompleteVisible.value = false
    nextTick(() => {
      ta?.focus()
      const pos = inputText.value.length
      ta?.setSelectionRange(pos, pos)
    })
  }

  if (!item.value.endsWith('/')) autocompleteVisible.value = false
}

// ── Keyboard handler ──────────────────────────────────────────────────────────

const handleKeydown = (e: KeyboardEvent) => {
  // Always intercept Tab inside the textarea
  if (e.key === 'Tab') {
    e.preventDefault()
    if (autocompleteVisible.value && autocompleteItems.value.length > 0) {
      const item = autocompleteItems.value[autocompleteIndex.value]
      if (item) selectAutocompleteItem(item)
    }
    return
  }

  if (autocompleteVisible.value) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      autocompleteIndex.value = (autocompleteIndex.value + 1) % autocompleteItems.value.length
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      autocompleteIndex.value =
        (autocompleteIndex.value - 1 + autocompleteItems.value.length) %
        autocompleteItems.value.length
      return
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      const item = autocompleteItems.value[autocompleteIndex.value]
      if (item) {
        e.preventDefault()
        selectAutocompleteItem(item)
        return
      }
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      autocompleteVisible.value = false
      return
    }
  }

  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

const handleInput = () => {
  updateAutocomplete(inputText.value)
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
      <p class="chat-empty-subtitle">
        Elige una conversación del panel izquierdo o crea una nueva para comenzar.
      </p>
    </div>

    <!-- Chat UI -->
    <template v-else>
      <!-- Workspace chip in header area -->
      <div v-if="currentWorkspace" class="workspace-bar">
        <i class="pi pi-folder-open workspace-bar-icon" />
        <span class="workspace-bar-path">{{ currentWorkspace }}</span>
        <button class="workspace-bar-clear" @click="currentWorkspace = ''" title="Clear workspace">
          <i class="pi pi-times" />
        </button>
      </div>

      <!-- Messages area -->
      <div ref="messagesEl" class="chat-messages">
        <!-- Empty conversation -->
        <div v-if="messages.length === 0 && !isStreaming" class="chat-placeholder">
          <i class="pi pi-sparkles chat-placeholder-icon" />
          <p class="chat-placeholder-text">Escribe un mensaje para comenzar la conversación</p>
          <p class="chat-placeholder-hint">
            Use <code>/new</code>, <code>/clear</code>, <code>/workspace /path</code>,
            <code>/model</code> &mdash; or <code>@file</code>, <code>@dir/</code>,
            <code>@https://...</code>, <code>@@glob/**</code>
          </p>
        </div>

        <!-- Message list -->
        <template v-for="msg in messages" :key="msg.id">
          <!-- System message (centered, muted) -->
          <div v-if="msg.role === 'system'" class="msg-system">
            <i class="pi pi-info-circle msg-system-icon" />
            <span class="msg-system-text">{{ msg.content }}</span>
          </div>

          <!-- User / assistant message -->
          <div
            v-else
            :class="['msg-row', msg.role === 'user' ? 'msg-row--user' : 'msg-row--assistant']"
          >
            <!-- Avatar -->
            <div
              :class="[
                'msg-avatar',
                msg.role === 'user' ? 'msg-avatar--user' : 'msg-avatar--assistant',
              ]"
            >
              <i :class="['pi', msg.role === 'user' ? 'pi-user' : 'pi-android']" />
            </div>

            <!-- Bubble -->
            <div
              :class="[
                'msg-bubble',
                msg.role === 'user' ? 'msg-bubble--user' : 'msg-bubble--assistant',
              ]"
            >
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
                  <i
                    :class="[
                      'pi',
                      isShellExpanded(msg.id) ? 'pi-chevron-up' : 'pi-chevron-down',
                      'shell-toggle-chevron',
                    ]"
                  />
                </button>
                <div v-if="isShellExpanded(msg.id)" class="shell-output">
                  <div v-for="(line, i) in msg.shellOutput" :key="i" class="shell-line">
                    {{ line }}
                  </div>
                </div>
              </div>

              <!-- Thinking indicator -->
              <div
                v-if="
                  msg.isStreaming &&
                  msg.content === '' &&
                  msg.toolCalls.filter((t) => !t.done).length === 0
                "
                class="thinking-indicator"
              >
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
        </template>
      </div>

      <!-- Input area -->
      <div class="chat-input-area">
        <!-- Autocomplete dropdown (positioned above input) -->
        <div
          v-if="autocompleteVisible && autocompleteItems.length > 0"
          class="autocomplete-dropdown"
        >
          <div
            v-for="(item, idx) in autocompleteItems"
            :key="item.label"
            :class="[
              'autocomplete-item',
              idx === autocompleteIndex ? 'autocomplete-item--active' : '',
            ]"
            @mousedown.prevent="selectAutocompleteItem(item)"
          >
            <span class="autocomplete-item-label">{{ item.label }}</span>
            <span v-if="item.hint" class="autocomplete-item-hint">{{ item.hint }}</span>
          </div>
        </div>

        <div class="chat-input-wrapper">
          <Textarea
            ref="textareaEl"
            v-model="inputText"
            placeholder="Message... (/ for commands, @ to reference files/URLs)"
            :disabled="isStreaming || !conversationId"
            :rows="1"
            auto-resize
            class="chat-textarea"
            @keydown="handleKeydown"
            @input="handleInput"
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
          Enter to send &middot; Shift+Enter for new line &middot;
          <span class="hint-code">/</span> commands &middot;
          <span class="hint-code">@</span> references
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
            >
              {{ line.text }}
            </div>
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
  flex: 1;
  min-height: 0;
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

.chat-placeholder-hint {
  font-size: 0.78rem;
  color: var(--do-text-muted);
  opacity: 0.6;
  margin: 0;
}

.chat-placeholder-hint code {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.8em;
  background: rgba(255, 255, 255, 0.07);
  border-radius: 3px;
  padding: 0.1em 0.35em;
  color: var(--do-blue);
}

/* ── Workspace bar ────────────────────────────────────────────────────── */
.workspace-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 1rem;
  background: rgba(10, 207, 131, 0.06);
  border-bottom: 1px solid rgba(10, 207, 131, 0.15);
  flex-shrink: 0;
}

.workspace-bar-icon {
  font-size: 0.75rem;
  color: var(--do-success);
  flex-shrink: 0;
}

.workspace-bar-path {
  font-size: 0.78rem;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: var(--do-success);
  opacity: 0.85;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.workspace-bar-clear {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--do-text-muted);
  padding: 0.15rem 0.25rem;
  border-radius: 3px;
  display: flex;
  align-items: center;
  transition: color 0.15s;
  flex-shrink: 0;
}

.workspace-bar-clear:hover {
  color: var(--do-text);
}

.workspace-bar-clear .pi {
  font-size: 0.65rem;
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

/* ── System message ───────────────────────────────────────────────────── */
.msg-system {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.35rem 0.75rem;
  align-self: center;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 1rem;
  max-width: 85%;
}

.msg-system-icon {
  font-size: 0.7rem;
  color: var(--do-text-muted);
  flex-shrink: 0;
}

.msg-system-text {
  font-size: 0.78rem;
  color: var(--do-text-muted);
  font-style: italic;
  white-space: pre-wrap;
  word-break: break-word;
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
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
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

.thinking-dot:nth-child(2) {
  animation-delay: 0.2s;
}
.thinking-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes thinking-bounce {
  0%,
  80%,
  100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  40% {
    transform: translateY(-5px);
    opacity: 1;
  }
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
  to {
    transform: rotate(360deg);
  }
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
  padding: 0.625rem 1rem 0.375rem;
  background: rgba(6, 13, 26, 0.95);
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(12px);
  position: relative;
}

.chat-input-wrapper {
  display: flex;
  gap: 0.5rem;
  align-items: flex-end;
}

/* ── Autocomplete dropdown ────────────────────────────────────────────── */
.autocomplete-dropdown {
  position: absolute;
  bottom: calc(100% - 0.875rem);
  left: 1rem;
  right: 3.5rem;
  background: #0f1e35;
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 0.5rem;
  overflow: hidden;
  z-index: 100;
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.4);
}

.autocomplete-item {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
  transition: background 0.1s;
}

.autocomplete-item:hover,
.autocomplete-item--active {
  background: rgba(59, 130, 246, 0.12);
}

.autocomplete-item-label {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.82rem;
  color: var(--do-blue);
  white-space: nowrap;
}

.autocomplete-item-hint {
  font-size: 0.75rem;
  color: var(--do-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
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

.hint-code {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.85em;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  padding: 0.05em 0.3em;
  color: var(--do-blue);
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
