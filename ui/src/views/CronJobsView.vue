<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { useCronJobs } from '@/composables/useCronJobs'
import type { CronJob as Job, CronJobInput as JobInput, CronJobRunResult as RunResult } from '@/types/cronJobs'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import InputSwitch from 'primevue/inputswitch'
import Toast from 'primevue/toast'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import Message from 'primevue/message'

// ─── State ────────────────────────────────────────────────────────────────────

const { t } = useI18n()
const toast = useToast()
const {
  jobs,
  isLoading: loading,
  isSubmitting: submitting,
  loadJobs: loadCronJobs,
  createJob: saveJob,
  deleteJob: removeJob,
  runJob: executeJob,
} = useCronJobs()
const runningJobId = ref<string | null>(null)
const deletingJobId = ref<string | null>(null)
const showCreateForm = ref(false)
const showDeleteConfirm = ref(false)
const jobToDelete = ref<Job | null>(null)
const lastRunResult = ref<RunResult | null>(null)
const showRunResult = ref(false)

// ─── Dropdown options ─────────────────────────────────────────────────────────

const sourceTypeOptions = computed(() => [
  { label: t('cronJobs.sourceCommand'), value: 'system_command' },
  { label: 'HTTP GET', value: 'http_get' },
  { label: t('cronJobs.sourceStatic'), value: 'static' },
])

const destinationTypeOptions = computed(() => [
  { label: t('cronJobs.destWhatsApp'), value: 'whatsapp' },
  { label: t('cronJobs.destTelegram'), value: 'telegram' },
  { label: t('cronJobs.destSlack'), value: 'slack' },
  { label: t('cronJobs.destNone'), value: 'none' },
])

const cronExamples = computed(() => [
  { label: t('cronJobs.every5min'), value: '*/5 * * * *' },
  { label: t('cronJobs.everyHour'), value: '0 * * * *' },
  { label: t('cronJobs.daily9am'), value: '0 9 * * *' },
  { label: t('cronJobs.weekdays8am'), value: '0 8 * * 1-5' },
  { label: t('cronJobs.sunMidnight'), value: '0 0 * * 0' },
])

// ─── Form state ───────────────────────────────────────────────────────────────

const emptyForm = (): JobInput => ({
  name: '',
  description: '',
  cron_expr: '',
  source_type: 'static',
  source_params: {},
  destination_type: 'none',
  destination_params: {},
  message_template: '{{output}}',
  enabled: true,
})

const form = reactive<JobInput>(emptyForm())

const validationErrors = reactive({
  name: '',
  cron_expr: '',
  source_params: '',
  destination_params: '',
})

// ─── Computed helpers ─────────────────────────────────────────────────────────

const sourceParamKey = computed(() => {
  if (form.source_type === 'system_command') return 'command'
  if (form.source_type === 'http_get') return 'url'
  if (form.source_type === 'static') return 'text'
  return ''
})

const sourceParamLabel = computed(() => {
  if (form.source_type === 'system_command') return t('cronJobs.command')
  if (form.source_type === 'http_get') return t('cronJobs.url')
  if (form.source_type === 'static') return t('cronJobs.text')
  return ''
})

const sourceParamPlaceholder = computed(() => {
  if (form.source_type === 'system_command') return 'df -h / uptime'
  if (form.source_type === 'http_get') return 'https://api.example.com/data'
  if (form.source_type === 'static') return t('cronJobs.text')
  return ''
})

const destinationParamKey = computed(() => {
  if (form.destination_type === 'whatsapp') return 'phone'
  if (form.destination_type === 'telegram') return 'chat_id'
  if (form.destination_type === 'slack') return 'channel'
  return ''
})

const destinationParamLabel = computed(() => {
  if (form.destination_type === 'whatsapp') return t('cronJobs.phone')
  if (form.destination_type === 'telegram') return 'Chat ID'
  if (form.destination_type === 'slack') return t('cronJobs.channel')
  return ''
})

const destinationParamPlaceholder = computed(() => {
  if (form.destination_type === 'whatsapp') return '+5491112345678'
  if (form.destination_type === 'telegram') return '-1001234567890'
  if (form.destination_type === 'slack') return '#general'
  return ''
})

// ─── API actions ──────────────────────────────────────────────────────────────

const loadJobs = async () => {
  try {
    await loadCronJobs()
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('cronJobs.errorLoad'),
      detail: err instanceof Error ? err.message : t('common.unknownError'),
      life: 4000,
    })
  }
}

const validateForm = (): boolean => {
  validationErrors.name = !form.name.trim() ? t('cronJobs.nameRequired') : ''
  validationErrors.cron_expr = !form.cron_expr.trim() ? t('cronJobs.cronRequired') : ''

  const sourceKey = sourceParamKey.value
  const sourceValue = sourceKey ? (form.source_params[sourceKey] ?? '') : ''
  validationErrors.source_params =
    sourceKey && !sourceValue.trim()
      ? t('cronJobs.fieldRequired', { field: sourceParamLabel.value })
      : ''

  const destKey = destinationParamKey.value
  const destValue = destKey ? (form.destination_params[destKey] ?? '') : ''
  validationErrors.destination_params =
    destKey && !destValue.trim()
      ? t('cronJobs.fieldRequired', { field: destinationParamLabel.value })
      : ''

  return !Object.values(validationErrors).some(Boolean)
}

const handleSourceTypeChange = () => {
  form.source_params = {}
}

const handleDestinationTypeChange = () => {
  form.destination_params = {}
}

const createJob = async () => {
  if (!validateForm()) {
    toast.add({
      severity: 'warn',
      summary: t('cronJobs.requiredFields'),
      detail: t('common.completeRequired'),
      life: 3000,
    })
    return
  }

  try {
    await saveJob(form)
    toast.add({ severity: 'success', summary: t('cronJobs.taskCreated'), life: 3000 })
    resetForm()
    showCreateForm.value = false
    await loadJobs()
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('cronJobs.errorCreate'),
      detail: err instanceof Error ? err.message : t('common.unknownError'),
      life: 4000,
    })
  }
}

const confirmDelete = (job: Job) => {
  jobToDelete.value = job
  showDeleteConfirm.value = true
}

const deleteJob = async () => {
  if (!jobToDelete.value) return
  deletingJobId.value = jobToDelete.value.id
  showDeleteConfirm.value = false
  try {
    await removeJob(jobToDelete.value.id)
    toast.add({ severity: 'success', summary: t('cronJobs.taskDeleted'), life: 3000 })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('cronJobs.errorDelete'),
      detail: err instanceof Error ? err.message : t('common.unknownError'),
      life: 4000,
    })
  } finally {
    deletingJobId.value = null
    jobToDelete.value = null
  }
}

const runJob = async (job: Job) => {
  runningJobId.value = job.id
  try {
    const res = await executeJob(job.id)
    lastRunResult.value = res
    showRunResult.value = true
    await loadJobs()
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('cronJobs.errorRun'),
      detail: err instanceof Error ? err.message : t('common.unknownError'),
      life: 4000,
    })
  } finally {
    runningJobId.value = null
  }
}

const resetForm = () => {
  Object.assign(form, emptyForm())
  validationErrors.name = ''
  validationErrors.cron_expr = ''
  validationErrors.source_params = ''
  validationErrors.destination_params = ''
}

const applyCronExample = (value: string) => {
  form.cron_expr = value
}

// ─── Display helpers ──────────────────────────────────────────────────────────

const formatDate = (iso: string | null): string => {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const sourceTypeLabel = (value: string): string => {
  return sourceTypeOptions.value.find((o) => o.value === value)?.label ?? value
}

const destinationTypeLabel = (value: string): string => {
  return destinationTypeOptions.value.find((o) => o.value === value)?.label ?? value
}

const statusSeverity = (status: string): 'success' | 'warn' | 'danger' | 'info' => {
  if (status === 'success') return 'success'
  if (status === 'error' || status === 'failed') return 'danger'
  if (status === 'running') return 'info'
  return 'warn'
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(loadJobs)
</script>

<template>
  <div class="cronjobs-container">
    <!-- Header -->
    <div class="header-section">
      <div class="integration-header">
        <div class="icon-wrapper cron-icon">
          <i class="pi pi-clock"></i>
        </div>
        <div class="header-content">
          <h1 class="integration-title">{{ t('cronJobs.title') }}</h1>
          <p class="integration-subtitle">{{ t('cronJobs.subtitle') }}</p>
        </div>
        <Button
          :label="t('cronJobs.newTask')"
          icon="pi pi-plus"
          severity="primary"
          class="new-job-btn"
          @click="showCreateForm = true"
        />
      </div>
    </div>

    <!-- Job list -->
    <div class="jobs-section">
      <!-- Loading -->
      <div v-if="loading" class="panel state-panel">
        <div class="centered-state">
          <i class="pi pi-spin pi-spinner state-icon"></i>
          <p>{{ t('cronJobs.loadingTasks') }}</p>
        </div>
      </div>

      <!-- Empty -->
      <div v-else-if="jobs.length === 0" class="panel state-panel">
        <div class="centered-state">
          <i class="pi pi-calendar-times state-icon empty-icon"></i>
          <h3>{{ t('cronJobs.noTasks') }}</h3>
          <p>{{ t('cronJobs.noTasksDesc') }}</p>
          <Button
            :label="t('cronJobs.createFirstTask')"
            icon="pi pi-plus"
            severity="primary"
            @click="showCreateForm = true"
          />
        </div>
      </div>

      <!-- Job cards -->
      <div v-else class="jobs-grid">
        <div v-for="job in jobs" :key="job.id" class="job-card">
          <div class="job-card-inner">
            <div class="job-header-row">
              <div class="job-title-block">
                <span class="job-name">{{ job.name }}</span>
                <span v-if="job.description" class="job-description">{{ job.description }}</span>
              </div>
              <div class="job-badges">
                <Tag
                  :value="job.enabled ? t('cronJobs.active') : t('cronJobs.inactive')"
                  :severity="job.enabled ? 'success' : 'secondary'"
                  class="enabled-tag"
                />
                <Tag
                  v-if="job.status"
                  :value="job.status"
                  :severity="statusSeverity(job.status)"
                  class="status-tag"
                />
              </div>
            </div>

            <div class="job-meta-grid">
              <div class="meta-item">
                <span class="meta-label"><i class="pi pi-clock"></i> {{ t('cronJobs.cron') }}</span>
                <code class="meta-value cron-value">{{ job.cron_expr }}</code>
              </div>
              <div class="meta-item">
                <span class="meta-label"
                  ><i class="pi pi-arrow-right-arrow-left"></i> {{ t('cronJobs.flow') }}</span
                >
                <span class="meta-value flow-value">
                  <span class="flow-badge source">{{ sourceTypeLabel(job.source_type) }}</span>
                  <i class="pi pi-arrow-right flow-arrow"></i>
                  <span class="flow-badge dest">{{
                    destinationTypeLabel(job.destination_type)
                  }}</span>
                </span>
              </div>
              <div class="meta-item">
                <span class="meta-label"
                  ><i class="pi pi-history"></i> {{ t('cronJobs.lastRun') }}</span
                >
                <span class="meta-value">{{ formatDate(job.last_run_at) }}</span>
              </div>
              <div v-if="job.last_result" class="meta-item meta-item--full">
                <span class="meta-label"
                  ><i class="pi pi-info-circle"></i> {{ t('cronJobs.lastResult') }}</span
                >
                <code class="meta-value result-value">{{ job.last_result }}</code>
              </div>
            </div>

            <div class="job-actions">
              <Button
                :label="t('cronJobs.runNow')"
                icon="pi pi-play"
                severity="success"
                size="small"
                :loading="runningJobId === job.id"
                :disabled="runningJobId !== null"
                @click="runJob(job)"
              />
              <Button
                :label="t('cronJobs.delete')"
                icon="pi pi-trash"
                severity="danger"
                size="small"
                outlined
                :loading="deletingJobId === job.id"
                :disabled="deletingJobId !== null"
                @click="confirmDelete(job)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create job dialog -->
    <Dialog
      v-model:visible="showCreateForm"
      :header="t('cronJobs.newTaskDialog')"
      :style="{ width: '640px', maxWidth: '96vw' }"
      modal
      :draggable="false"
      @hide="resetForm"
    >
      <form class="create-form" @submit.prevent="createJob">
        <!-- Name -->
        <div class="field-group">
          <label class="field-label">
            <i class="pi pi-tag field-icon"></i>
            {{ t('cronJobs.taskName') }}
            <span class="required">*</span>
          </label>
          <InputText
            v-model="form.name"
            :placeholder="t('cronJobs.taskNamePlaceholder')"
            :invalid="!!validationErrors.name"
            class="w-full"
          />
          <Message v-if="validationErrors.name" severity="error" class="field-error">
            {{ validationErrors.name }}
          </Message>
        </div>

        <!-- Description -->
        <div class="field-group">
          <label class="field-label">
            <i class="pi pi-align-left field-icon"></i>
            {{ t('cronJobs.taskDescription') }}
            <span class="optional">({{ t('common.optional') }})</span>
          </label>
          <InputText
            v-model="form.description"
            :placeholder="t('cronJobs.taskDescriptionPlaceholder')"
            class="w-full"
          />
        </div>

        <!-- Cron expression -->
        <div class="field-group">
          <label class="field-label">
            <i class="pi pi-clock field-icon"></i>
            {{ t('cronJobs.cronExpression') }}
            <span class="required">*</span>
          </label>
          <InputText
            v-model="form.cron_expr"
            placeholder="*/5 * * * *"
            :invalid="!!validationErrors.cron_expr"
            class="w-full"
          />
          <Message v-if="validationErrors.cron_expr" severity="error" class="field-error">
            {{ validationErrors.cron_expr }}
          </Message>
          <div class="cron-examples">
            <span class="examples-label">{{ t('cronJobs.examples') }}:</span>
            <button
              v-for="ex in cronExamples"
              :key="ex.value"
              type="button"
              class="cron-chip"
              @click="applyCronExample(ex.value)"
            >
              {{ ex.label }} <code>{{ ex.value }}</code>
            </button>
          </div>
        </div>

        <!-- Source type -->
        <div class="field-group">
          <label class="field-label">
            <i class="pi pi-database field-icon"></i>
            {{ t('cronJobs.sourceType') }}
          </label>
          <Dropdown
            v-model="form.source_type"
            :options="sourceTypeOptions"
            option-label="label"
            option-value="value"
            class="w-full"
            @change="handleSourceTypeChange"
          />
        </div>

        <!-- Source params (dynamic) -->
        <div v-if="sourceParamKey" class="field-group field-group--indented">
          <label class="field-label">
            <i class="pi pi-arrow-right field-icon"></i>
            {{ sourceParamLabel }}
            <span class="required">*</span>
          </label>
          <Textarea
            v-if="form.source_type === 'static'"
            v-model="form.source_params[sourceParamKey]"
            :placeholder="sourceParamPlaceholder"
            :invalid="!!validationErrors.source_params"
            rows="3"
            class="w-full"
          />
          <InputText
            v-else
            v-model="form.source_params[sourceParamKey]"
            :placeholder="sourceParamPlaceholder"
            :invalid="!!validationErrors.source_params"
            class="w-full"
          />
          <Message v-if="validationErrors.source_params" severity="error" class="field-error">
            {{ validationErrors.source_params }}
          </Message>
        </div>

        <!-- Destination type -->
        <div class="field-group">
          <label class="field-label">
            <i class="pi pi-send field-icon"></i>
            {{ t('cronJobs.destinationType') }}
          </label>
          <Dropdown
            v-model="form.destination_type"
            :options="destinationTypeOptions"
            option-label="label"
            option-value="value"
            class="w-full"
            @change="handleDestinationTypeChange"
          />
        </div>

        <!-- Destination params (dynamic) -->
        <div v-if="destinationParamKey" class="field-group field-group--indented">
          <label class="field-label">
            <i class="pi pi-arrow-right field-icon"></i>
            {{ destinationParamLabel }}
            <span class="required">*</span>
          </label>
          <InputText
            v-model="form.destination_params[destinationParamKey]"
            :placeholder="destinationParamPlaceholder"
            :invalid="!!validationErrors.destination_params"
            class="w-full"
          />
          <Message v-if="validationErrors.destination_params" severity="error" class="field-error">
            {{ validationErrors.destination_params }}
          </Message>
        </div>

        <!-- Message template -->
        <div class="field-group">
          <label class="field-label">
            <i class="pi pi-file-edit field-icon"></i>
            {{ t('cronJobs.messageTemplate') }}
          </label>
          <InputText
            v-model="form.message_template"
            :placeholder="t('cronJobs.messageTemplatePlaceholder')"
            class="w-full"
          />
          <small class="field-help">{{ t('cronJobs.messageTemplateHelp') }}</small>
        </div>

        <!-- Enabled toggle -->
        <div class="field-group field-group--row">
          <label class="field-label">
            <i class="pi pi-power-off field-icon"></i>
            {{ t('cronJobs.enabledOnCreate') }}
          </label>
          <InputSwitch v-model="form.enabled" class="modern-switch" />
        </div>

        <div class="dialog-actions">
          <Button
            type="button"
            :label="t('common.cancel')"
            severity="secondary"
            outlined
            @click="showCreateForm = false"
          />
          <Button
            type="submit"
            :label="t('cronJobs.createTask')"
            icon="pi pi-check"
            severity="primary"
            :loading="submitting"
          />
        </div>
      </form>
    </Dialog>

    <!-- Delete confirmation dialog -->
    <Dialog
      v-model:visible="showDeleteConfirm"
      :header="t('cronJobs.confirmDeleteTitle')"
      :style="{ width: '420px', maxWidth: '96vw' }"
      modal
      :draggable="false"
    >
      <div class="confirm-body">
        <i class="pi pi-exclamation-triangle confirm-icon"></i>
        <p>
          {{ t('cronJobs.confirmDeleteMsg') }} <strong>{{ jobToDelete?.name }}</strong
          >?
        </p>
      </div>
      <div class="dialog-actions">
        <Button
          :label="t('common.cancel')"
          severity="secondary"
          outlined
          @click="showDeleteConfirm = false"
        />
        <Button
          :label="t('common.delete')"
          icon="pi pi-trash"
          severity="danger"
          @click="deleteJob"
        />
      </div>
    </Dialog>

    <!-- Run result dialog -->
    <Dialog
      v-model:visible="showRunResult"
      :header="t('cronJobs.runResult')"
      :style="{ width: '520px', maxWidth: '96vw' }"
      modal
      :draggable="false"
    >
      <div v-if="lastRunResult" class="run-result-body">
        <div class="result-status-row">
          <Tag :value="lastRunResult.status" :severity="statusSeverity(lastRunResult.status)" />
        </div>
        <div class="result-output">
          <span class="meta-label">{{ t('cronJobs.runResult') }}</span>
          <pre class="result-pre">{{ lastRunResult.result }}</pre>
        </div>
      </div>
      <div class="dialog-actions">
        <Button :label="t('common.close')" severity="secondary" @click="showRunResult = false" />
      </div>
    </Dialog>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.cronjobs-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1rem 1.25rem;
  min-height: 100vh;
  background: var(--do-bg);
  box-sizing: border-box;
}

/* ─── Header ──────────────────────────────────────────────────────────────── */

.header-section {
  margin-bottom: 1.5rem;
}

.integration-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.icon-wrapper {
  width: 3.2rem;
  height: 3.2rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  color: #fff;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}

.cron-icon {
  background: linear-gradient(135deg, #f59e0b 0%, #b45309 100%);
}

.header-content {
  flex: 1;
  min-width: 0;
}

.integration-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 0.25rem 0;
  color: var(--do-text);
}

.integration-subtitle {
  font-size: 0.95rem;
  color: var(--do-text-muted);
  margin: 0;
}

.new-job-btn {
  margin-left: auto;
  flex-shrink: 0;
}

/* ─── State panels ────────────────────────────────────────────────────────── */

.panel {
  border: 1px solid var(--do-border-light);
  border-radius: 0.75rem;
  overflow: hidden;
  background: var(--do-bg);
}

.state-panel {
  margin-bottom: 1rem;
}

.centered-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem 1rem;
  text-align: center;
}

.state-icon {
  font-size: 2.5rem;
  color: var(--color-primary);
}

.empty-icon {
  color: var(--do-text-muted);
}

.centered-state h3 {
  margin: 0;
  color: var(--do-text);
}

.centered-state p {
  margin: 0;
  color: var(--do-text-muted);
  font-size: 0.95rem;
}

/* ─── Jobs grid ───────────────────────────────────────────────────────────── */

.jobs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.job-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--do-border-light);
  border-radius: 0.75rem;
  overflow: hidden;
  transition:
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.job-card:hover {
  box-shadow: 0 10px 32px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.job-card-inner {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1rem;
}

.job-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.job-title-block {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.job-name {
  font-size: 1rem;
  font-weight: 700;
  color: var(--do-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.job-description {
  font-size: 0.82rem;
  color: var(--do-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.job-badges {
  display: flex;
  gap: 0.4rem;
  flex-shrink: 0;
  flex-wrap: wrap;
  justify-content: flex-end;
}

/* ─── Meta grid ───────────────────────────────────────────────────────────── */

.job-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--do-border-light);
  border-radius: 0.5rem;
  padding: 0.5rem 0.65rem;
}

.meta-item--full {
  grid-column: 1 / -1;
}

.meta-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--do-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.meta-label i {
  color: var(--color-primary);
}

.meta-value {
  font-size: 0.85rem;
  color: var(--do-text);
}

.cron-value {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  background: rgba(255, 255, 255, 0.08);
  padding: 0.15rem 0.4rem;
  border-radius: 0.3rem;
  color: var(--do-text);
  font-size: 0.82rem;
}

.flow-value {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  flex-wrap: wrap;
}

.flow-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
}

.flow-badge.source {
  background: rgba(59, 130, 246, 0.15);
  color: #93c5fd;
}

.flow-badge.dest {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
}

.flow-arrow {
  font-size: 0.7rem;
  color: var(--do-text-muted);
}

.result-value {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.8rem;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 3.5rem;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* ─── Job actions ─────────────────────────────────────────────────────────── */

.job-actions {
  display: flex;
  gap: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--do-border-light);
}

/* ─── Create form ─────────────────────────────────────────────────────────── */

.create-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-group--indented {
  padding-left: 1rem;
  border-left: 3px solid var(--do-border-light);
}

.field-group--row {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.field-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--do-text);
}

.required {
  color: var(--color-danger);
}

.optional {
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--do-text-muted);
}

.field-icon {
  color: var(--color-primary);
  font-size: 1rem;
}

.field-error {
  margin-top: 0.25rem;
}

.field-help {
  font-size: 0.82rem;
  color: var(--do-text-muted);
  font-style: italic;
}

.field-help code {
  background: rgba(255, 255, 255, 0.08);
  padding: 0.1rem 0.3rem;
  border-radius: 0.25rem;
  font-family: 'SF Mono', monospace;
  font-size: 0.8rem;
  color: var(--do-text);
}

.w-full {
  width: 100%;
}

/* ─── Cron examples ───────────────────────────────────────────────────────── */

.cron-examples {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.2rem;
}

.examples-label {
  font-size: 0.8rem;
  color: var(--do-text-muted);
  font-weight: 600;
  flex-shrink: 0;
}

.cron-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--do-border-light);
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  font-size: 0.78rem;
  color: var(--do-text-muted);
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s;
}

.cron-chip:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--do-border-light);
}

.cron-chip code {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.75rem;
  color: #93c5fd;
  background: rgba(59, 130, 246, 0.15);
  padding: 0.05rem 0.3rem;
  border-radius: 0.25rem;
}

/* ─── Dialog dark theme ───────────────────────────────────────────────────── */

:deep(.p-dialog) {
  background: var(--do-bg);
  border: 1px solid var(--do-border-light);
}

:deep(.p-dialog-header) {
  background: var(--do-bg);
  color: var(--do-text);
  border-bottom: 1px solid var(--do-border-light);
}

:deep(.p-dialog-content) {
  background: var(--do-bg);
}

:deep(.p-dialog-footer) {
  background: var(--do-bg);
  border-top: 1px solid var(--do-border-light);
}

:deep(.p-dropdown) {
  background: var(--do-bg);
  border-color: var(--do-border-light);
}

:deep(.p-dropdown-panel) {
  background: var(--do-bg);
  border-color: var(--do-border-light);
}

:deep(.p-inputtext) {
  background: var(--do-bg);
}

:deep(.p-textarea) {
  background: var(--do-bg);
}

/* ─── Dialog actions ──────────────────────────────────────────────────────── */

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--do-border-light);
  margin-top: 0.5rem;
}

/* ─── Delete confirm ──────────────────────────────────────────────────────── */

.confirm-body {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 0.5rem 0 1rem;
}

.confirm-icon {
  font-size: 2rem;
  color: var(--color-warning);
  flex-shrink: 0;
  margin-top: 0.1rem;
}

.confirm-body p {
  margin: 0;
  color: var(--do-text);
  line-height: 1.5;
}

/* ─── Run result ──────────────────────────────────────────────────────────── */

.run-result-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.25rem 0 0.5rem;
}

.result-status-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.result-output {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.result-pre {
  background: #1e293b;
  color: #e2e8f0;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.82rem;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 280px;
  overflow-y: auto;
  margin: 0;
}

:deep(.modern-switch) {
  transform: scale(1.1);
}

/* ─── Responsive ──────────────────────────────────────────────────────────── */

@media (max-width: 640px) {
  .cronjobs-container {
    padding: 0.75rem;
  }

  .integration-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .new-job-btn {
    margin-left: 0;
    width: 100%;
    justify-content: center;
  }

  .jobs-grid {
    grid-template-columns: 1fr;
  }

  .job-meta-grid {
    grid-template-columns: 1fr;
  }

  .job-badges {
    justify-content: flex-start;
  }

  .job-header-row {
    flex-direction: column;
  }

  .job-actions {
    flex-direction: column;
  }
}
</style>
