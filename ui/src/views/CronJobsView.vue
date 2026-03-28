<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import InputSwitch from 'primevue/inputswitch'
import Toast from 'primevue/toast'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import Message from 'primevue/message'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Job {
  id: string
  profile_id: string
  name: string
  description: string
  cron_expr: string
  source_type: string
  source_params: Record<string, string>
  destination_type: string
  destination_params: Record<string, string>
  message_template: string
  enabled: boolean
  status: string
  last_run_at: string | null
  last_result: string | null
  created_at: string
  updated_at: string
}

interface JobInput {
  name: string
  description: string
  cron_expr: string
  source_type: string
  source_params: Record<string, string>
  destination_type: string
  destination_params: Record<string, string>
  message_template: string
  enabled: boolean
}

interface RunResult {
  status: string
  result: string
}

// ─── API helpers ──────────────────────────────────────────────────────────────

const baseUrl = computed(() =>
  (import.meta.env.VITE_ASSISTANT_BASE_URL as string || 'http://localhost:8000').replace(/\/$/, '')
)

const apiHeaders = computed<Record<string, string>>(() => {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const apiKey = import.meta.env.VITE_ASSISTANT_API_KEY as string | undefined
  if (apiKey) headers['x-api-key'] = apiKey
  return headers
})

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${baseUrl.value}${path}`, {
    ...init,
    headers: { ...apiHeaders.value, ...(init.headers as Record<string, string> | undefined) },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(text || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ─── State ────────────────────────────────────────────────────────────────────

const toast = useToast()
const jobs = ref<Job[]>([])
const loading = ref(false)
const submitting = ref(false)
const runningJobId = ref<string | null>(null)
const deletingJobId = ref<string | null>(null)
const showCreateForm = ref(false)
const showDeleteConfirm = ref(false)
const jobToDelete = ref<Job | null>(null)
const lastRunResult = ref<RunResult | null>(null)
const showRunResult = ref(false)

// ─── Dropdown options ─────────────────────────────────────────────────────────

const sourceTypeOptions = [
  { label: 'Comando del sistema', value: 'system_command' },
  { label: 'HTTP GET', value: 'http_get' },
  { label: 'Texto estático', value: 'static' },
]

const destinationTypeOptions = [
  { label: 'WhatsApp', value: 'whatsapp' },
  { label: 'Telegram', value: 'telegram' },
  { label: 'Slack', value: 'slack' },
  { label: 'Ninguno', value: 'none' },
]

const cronExamples = [
  { label: 'Cada 5 minutos', value: '*/5 * * * *' },
  { label: 'Cada hora', value: '0 * * * *' },
  { label: 'Todos los días a las 9:00', value: '0 9 * * *' },
  { label: 'Lunes a viernes a las 8:00', value: '0 8 * * 1-5' },
  { label: 'Cada domingo a medianoche', value: '0 0 * * 0' },
]

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
  if (form.source_type === 'system_command') return 'Comando'
  if (form.source_type === 'http_get') return 'URL'
  if (form.source_type === 'static') return 'Texto'
  return ''
})

const sourceParamPlaceholder = computed(() => {
  if (form.source_type === 'system_command') return 'df -h / uptime'
  if (form.source_type === 'http_get') return 'https://api.example.com/data'
  if (form.source_type === 'static') return 'Texto que se enviará al destino'
  return ''
})

const destinationParamKey = computed(() => {
  if (form.destination_type === 'whatsapp') return 'phone'
  if (form.destination_type === 'telegram') return 'chat_id'
  if (form.destination_type === 'slack') return 'channel'
  return ''
})

const destinationParamLabel = computed(() => {
  if (form.destination_type === 'whatsapp') return 'Teléfono'
  if (form.destination_type === 'telegram') return 'Chat ID'
  if (form.destination_type === 'slack') return 'Canal'
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
  loading.value = true
  try {
    const res = await apiFetch<{ data: Job[] }>('/api/v1/jobs')
    jobs.value = res.data ?? []
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Error al cargar tareas',
      detail: err instanceof Error ? err.message : 'Error desconocido',
      life: 4000,
    })
  } finally {
    loading.value = false
  }
}

const validateForm = (): boolean => {
  validationErrors.name = !form.name.trim() ? 'El nombre es obligatorio.' : ''
  validationErrors.cron_expr = !form.cron_expr.trim() ? 'La expresión cron es obligatoria.' : ''

  const sourceKey = sourceParamKey.value
  const sourceValue = sourceKey ? (form.source_params[sourceKey] ?? '') : ''
  validationErrors.source_params =
    sourceKey && !sourceValue.trim() ? `El campo "${sourceParamLabel.value}" es obligatorio.` : ''

  const destKey = destinationParamKey.value
  const destValue = destKey ? (form.destination_params[destKey] ?? '') : ''
  validationErrors.destination_params =
    destKey && !destValue.trim() ? `El campo "${destinationParamLabel.value}" es obligatorio.` : ''

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
      summary: 'Campos requeridos',
      detail: 'Por favor completa todos los campos obligatorios.',
      life: 3000,
    })
    return
  }

  submitting.value = true
  try {
    await apiFetch<{ data: Job }>('/api/v1/jobs', {
      method: 'POST',
      body: JSON.stringify(form),
    })
    toast.add({ severity: 'success', summary: 'Tarea creada', life: 3000 })
    resetForm()
    showCreateForm.value = false
    await loadJobs()
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Error al crear tarea',
      detail: err instanceof Error ? err.message : 'Error desconocido',
      life: 4000,
    })
  } finally {
    submitting.value = false
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
    await apiFetch(`/api/v1/jobs/${jobToDelete.value.id}`, { method: 'DELETE' })
    toast.add({ severity: 'success', summary: 'Tarea eliminada', life: 3000 })
    jobs.value = jobs.value.filter((j) => j.id !== jobToDelete.value!.id)
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Error al eliminar',
      detail: err instanceof Error ? err.message : 'Error desconocido',
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
    const res = await apiFetch<RunResult>(`/api/v1/jobs/${job.id}/run`, { method: 'POST' })
    lastRunResult.value = res
    showRunResult.value = true
    await loadJobs()
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Error al ejecutar tarea',
      detail: err instanceof Error ? err.message : 'Error desconocido',
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
  return sourceTypeOptions.find((o) => o.value === value)?.label ?? value
}

const destinationTypeLabel = (value: string): string => {
  return destinationTypeOptions.find((o) => o.value === value)?.label ?? value
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
          <h1 class="integration-title">Cron Jobs</h1>
          <p class="integration-subtitle">
            Gestiona tareas programadas: envía datos por WhatsApp, Telegram o Slack con frecuencia configurable
          </p>
        </div>
        <Button
          label="Nueva tarea"
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
      <div v-if="loading" class="state-card">
        <Card>
          <template #content>
            <div class="centered-state">
              <i class="pi pi-spin pi-spinner state-icon"></i>
              <p>Cargando tareas programadas…</p>
            </div>
          </template>
        </Card>
      </div>

      <!-- Empty -->
      <div v-else-if="jobs.length === 0" class="state-card">
        <Card>
          <template #content>
            <div class="centered-state">
              <i class="pi pi-calendar-times state-icon empty-icon"></i>
              <h3>Sin tareas programadas</h3>
              <p>Crea tu primera tarea para automatizar envíos periódicos</p>
              <Button
                label="Crear primera tarea"
                icon="pi pi-plus"
                severity="primary"
                @click="showCreateForm = true"
              />
            </div>
          </template>
        </Card>
      </div>

      <!-- Job cards -->
      <div v-else class="jobs-grid">
        <Card v-for="job in jobs" :key="job.id" class="job-card">
          <template #content>
            <div class="job-card-inner">

              <div class="job-header-row">
                <div class="job-title-block">
                  <span class="job-name">{{ job.name }}</span>
                  <span v-if="job.description" class="job-description">{{ job.description }}</span>
                </div>
                <div class="job-badges">
                  <Tag
                    :value="job.enabled ? 'Activo' : 'Inactivo'"
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
                  <span class="meta-label"><i class="pi pi-clock"></i> Cron</span>
                  <code class="meta-value cron-value">{{ job.cron_expr }}</code>
                </div>
                <div class="meta-item">
                  <span class="meta-label"><i class="pi pi-arrow-right-arrow-left"></i> Flujo</span>
                  <span class="meta-value flow-value">
                    <span class="flow-badge source">{{ sourceTypeLabel(job.source_type) }}</span>
                    <i class="pi pi-arrow-right flow-arrow"></i>
                    <span class="flow-badge dest">{{ destinationTypeLabel(job.destination_type) }}</span>
                  </span>
                </div>
                <div class="meta-item">
                  <span class="meta-label"><i class="pi pi-history"></i> Última ejecución</span>
                  <span class="meta-value">{{ formatDate(job.last_run_at) }}</span>
                </div>
                <div v-if="job.last_result" class="meta-item meta-item--full">
                  <span class="meta-label"><i class="pi pi-info-circle"></i> Último resultado</span>
                  <code class="meta-value result-value">{{ job.last_result }}</code>
                </div>
              </div>

              <div class="job-actions">
                <Button
                  label="Ejecutar ahora"
                  icon="pi pi-play"
                  severity="success"
                  size="small"
                  :loading="runningJobId === job.id"
                  :disabled="runningJobId !== null"
                  @click="runJob(job)"
                />
                <Button
                  label="Eliminar"
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
          </template>
        </Card>
      </div>
    </div>

    <!-- Create job dialog -->
    <Dialog
      v-model:visible="showCreateForm"
      header="Nueva tarea programada"
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
            Nombre
            <span class="required">*</span>
          </label>
          <InputText
            v-model="form.name"
            placeholder="Reporte diario de disco"
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
            Descripción
            <span class="optional">(opcional)</span>
          </label>
          <InputText
            v-model="form.description"
            placeholder="Descripción breve de la tarea"
            class="w-full"
          />
        </div>

        <!-- Cron expression -->
        <div class="field-group">
          <label class="field-label">
            <i class="pi pi-clock field-icon"></i>
            Expresión cron
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
            <span class="examples-label">Ejemplos:</span>
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
            Tipo de origen
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
            Tipo de destino
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
            Template del mensaje
          </label>
          <InputText
            v-model="form.message_template"
            placeholder="{{output}}"
            class="w-full"
          />
          <small class="field-help">
            Usa <code>&#123;&#123;output&#125;&#125;</code> para insertar el resultado del origen en el mensaje.
          </small>
        </div>

        <!-- Enabled toggle -->
        <div class="field-group field-group--row">
          <label class="field-label">
            <i class="pi pi-power-off field-icon"></i>
            Habilitada al crear
          </label>
          <InputSwitch v-model="form.enabled" class="modern-switch" />
        </div>

        <div class="dialog-actions">
          <Button
            type="button"
            label="Cancelar"
            severity="secondary"
            outlined
            @click="showCreateForm = false"
          />
          <Button
            type="submit"
            label="Crear tarea"
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
      header="Eliminar tarea"
      :style="{ width: '420px', maxWidth: '96vw' }"
      modal
      :draggable="false"
    >
      <div class="confirm-body">
        <i class="pi pi-exclamation-triangle confirm-icon"></i>
        <p>
          ¿Eliminar la tarea <strong>{{ jobToDelete?.name }}</strong>? Esta acción no se puede deshacer.
        </p>
      </div>
      <div class="dialog-actions">
        <Button
          label="Cancelar"
          severity="secondary"
          outlined
          @click="showDeleteConfirm = false"
        />
        <Button
          label="Eliminar"
          icon="pi pi-trash"
          severity="danger"
          @click="deleteJob"
        />
      </div>
    </Dialog>

    <!-- Run result dialog -->
    <Dialog
      v-model:visible="showRunResult"
      header="Resultado de ejecución"
      :style="{ width: '520px', maxWidth: '96vw' }"
      modal
      :draggable="false"
    >
      <div v-if="lastRunResult" class="run-result-body">
        <div class="result-status-row">
          <Tag
            :value="lastRunResult.status"
            :severity="statusSeverity(lastRunResult.status)"
          />
        </div>
        <div class="result-output">
          <span class="meta-label">Salida</span>
          <pre class="result-pre">{{ lastRunResult.result }}</pre>
        </div>
      </div>
      <div class="dialog-actions">
        <Button label="Cerrar" severity="secondary" @click="showRunResult = false" />
      </div>
    </Dialog>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.cronjobs-container {
  max-width: 1200px;
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
  color: white;
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

/* ─── State cards ─────────────────────────────────────────────────────────── */

.state-card {
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
  color: var(--color-primary, #6366f1);
}

.empty-icon {
  color: var(--do-text-secondary);
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
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  border: 1px solid var(--vt-c-gray-200);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.job-card:hover {
  box-shadow: 0 10px 32px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

:deep(.job-card .p-card-content) {
  padding: 1rem;
}

.job-card-inner {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
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
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--vt-c-gray-200);
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
  color: var(--color-primary, #6366f1);
}

.meta-value {
  font-size: 0.85rem;
  color: var(--do-text);
}

.cron-value {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  background: rgba(255,255,255,0.08);
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
  background: rgba(59,130,246,0.15);
  color: #93c5fd;
}

.flow-badge.dest {
  background: rgba(16,185,129,0.15);
  color: #6ee7b7;
}

.flow-arrow {
  font-size: 0.7rem;
  color: var(--do-text-secondary);
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
  border-top: 1px solid var(--vt-c-gray-200);
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
  border-left: 3px solid var(--vt-c-gray-200);
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
  color: var(--color-danger, #ef4444);
}

.optional {
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--do-text-secondary);
}

.field-icon {
  color: var(--color-primary, #6366f1);
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
  background: rgba(255,255,255,0.08);
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
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--vt-c-gray-200);
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  font-size: 0.78rem;
  color: var(--do-text-muted);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.cron-chip:hover {
  background: rgba(255,255,255,0.1);
  border-color: var(--do-text-secondary);
}

.cron-chip code {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.75rem;
  color: #93c5fd;
  background: rgba(59,130,246,0.15);
  padding: 0.05rem 0.3rem;
  border-radius: 0.25rem;
}

/* ─── Dialog actions ──────────────────────────────────────────────────────── */

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--vt-c-gray-200);
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
  color: #f59e0b;
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
