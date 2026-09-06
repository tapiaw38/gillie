<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'

interface ApprovalRequest {
  request_id: string
  tool_name: string
  target: string
  diff: string
  risk: string
}

interface Props {
  visible: boolean
  loading: boolean
  pendingApproval: ApprovalRequest | null
}

interface Emits {
  (event: 'update:visible', value: boolean): void
  (event: 'approve', feedback: string): void
  (event: 'reject', feedback: string): void
}

const NOTABLE_RISKS = ['write', 'execute', 'destructive']

const isNotableRisk = (risk?: string): boolean => !!risk && NOTABLE_RISKS.includes(risk)

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useI18n()

const feedback = ref('')

interface DiffLine {
  type: 'added' | 'removed' | 'context'
  text: string
}

const parseDiffLines = (diff: string): DiffLine[] => {
  return diff.split('\n').map((line) => {
    if (line.startsWith('+')) return { type: 'added' as const, text: line }
    if (line.startsWith('-')) return { type: 'removed' as const, text: line }
    return { type: 'context' as const, text: line }
  })
}

const handleApprove = () => {
  emit('approve', feedback.value)
  feedback.value = ''
}

const handleReject = () => {
  emit('reject', feedback.value)
  feedback.value = ''
}
</script>

<template>
  <Dialog
    :visible="props.visible"
    :closable="false"
    :draggable="false"
    :modal="true"
    :header="t('sandbox.approvalTitle')"
    class="approval-dialog"
    style="width: min(680px, 95vw)"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="approval-body">
      <div class="approval-warning">
        <i class="pi pi-exclamation-triangle approval-warning-icon" />
        <div>
          <p class="approval-warning-title">{{ t('sandbox.approvalTitle') }}</p>
          <p class="approval-warning-tool">
            {{ t('sandbox.approvalTool') }}: <strong>{{ pendingApproval?.tool_name }}</strong>
            <span
              v-if="isNotableRisk(pendingApproval?.risk)"
              :class="['approval-risk', `approval-risk--${pendingApproval?.risk}`]"
              >{{ pendingApproval?.risk }}</span
            >
            <template v-if="pendingApproval?.target">
              → <code>{{ pendingApproval.target }}</code>
            </template>
          </p>
        </div>
      </div>

      <div v-if="pendingApproval?.diff" class="diff-viewer">
        <p class="diff-label">{{ t('sandbox.approvalTitle') }}:</p>
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
        <label class="approval-feedback-label">{{
          t('sandbox.approvalFeedbackPlaceholder')
        }}</label>
        <Textarea
          v-model="feedback"
          :placeholder="t('sandbox.approvalFeedbackPlaceholder')"
          :rows="2"
          auto-resize
          class="approval-feedback-input"
        />
      </div>
    </div>

    <template #footer>
      <div class="approval-footer">
        <Button
          :label="t('sandbox.approvalReject')"
          icon="pi pi-times"
          severity="danger"
          outlined
          :loading="props.loading"
          @click="handleReject"
        />
        <Button
          :label="t('sandbox.approvalApprove')"
          icon="pi pi-check"
          severity="success"
          :loading="props.loading"
          @click="handleApprove"
        />
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
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

.approval-risk {
  margin-left: 0.4rem;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  background: rgba(245, 166, 35, 0.22);
}

.approval-risk--execute,
.approval-risk--destructive {
  background: rgba(226, 66, 66, 0.25);
  color: var(--do-danger, #e24242);
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
</style>
