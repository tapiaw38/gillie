<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Toast from 'primevue/toast'
import Dropdown from 'primevue/dropdown'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { useAssistant } from '@/composables/useAssistant'
import WorkflowEditor from '@/components/workflow/WorkflowEditor.vue'
import WorkflowGuideModal from '@/components/workflow/WorkflowGuideModal.vue'
import type { WorkflowFunction } from '@/types/workflow.types'

const toast = useToast()
const { t } = useI18n()

const { getAssistantProfile, updateAssistantProfile, assistantProfile } = useAssistant()

const jsonContent = ref('')
const isEditing = ref(false)
const isSaving = ref(false)
const jsonError = ref('')
const editorMode = ref<'json' | 'visual'>('json')
const currentWorkflow = ref<WorkflowFunction | null>(null)
const showGuideModal = ref(false)
const selectedWorkflowIndex = ref(0)

const showWorkflowVisual = ref(false)

const sampleJson = [
  {
    type: 'workflow',
    name: 'reserva_habitacion',
    description: 'Reserva de habitación completa',
    input_params: ['guest_name', 'email', 'check_in'],
    keywords: ['reserva', 'hotel', 'booking'],
    steps: [
      {
        name: 'crear_reserva',
        url: 'localhost:8085/api/bookings',
        method: 'POST',
        required_params: ['guest_name', 'email'],
        body_template: '{"name": "{guest_name}"}',
      },
    ],
  },
]

const allFunctions = computed(() => {
  try {
    const parsed = JSON.parse(jsonContent.value)
    if (Array.isArray(parsed)) return parsed
    if (parsed.functions && Array.isArray(parsed.functions)) return parsed.functions
    return []
  } catch {
    return []
  }
})

const availableWorkflows = computed<WorkflowFunction[]>(() => {
  try {
    const parsed = JSON.parse(jsonContent.value)
    if (Array.isArray(parsed)) {
      return parsed.filter((f: WorkflowFunction) => f.type === 'workflow')
    } else if (parsed.functions && Array.isArray(parsed.functions)) {
      return parsed.functions.filter((f: WorkflowFunction) => f.type === 'workflow')
    }
    return []
  } catch {
    return []
  }
})

const hasWorkflow = (): boolean => availableWorkflows.value.length > 0

onMounted(async () => {
  await getAssistantProfile()

  if (assistantProfile.value?.functions && assistantProfile.value.functions.trim() !== '') {
    jsonContent.value = assistantProfile.value.functions
  } else {
    jsonContent.value = JSON.stringify(sampleJson, null, 2)
  }
})

const validateJson = (jsonString: string): boolean => {
  try {
    const parsed = JSON.parse(jsonString)

    if (Array.isArray(parsed)) {
      for (const func of parsed) {
        if (!func.name || !func.description || !func.type) {
          jsonError.value = t('functions.eachFunctionRequired')
          return false
        }
      }
    } else if (parsed.functions && Array.isArray(parsed.functions)) {
      for (const func of parsed.functions) {
        if (!func.name || !func.description || !func.type) {
          jsonError.value = t('functions.eachFunctionRequired')
          return false
        }
      }
    } else {
      jsonError.value = t('functions.jsonMustBeArray')
      return false
    }

    jsonError.value = ''
    return true
  } catch (error) {
    jsonError.value = `${t('functions.jsonSyntaxError')}: ${
      error instanceof Error ? error.message : t('common.unknownError')
    }`
    return false
  }
}

const formatJson = () => {
  if (validateJson(jsonContent.value)) {
    try {
      const parsed = JSON.parse(jsonContent.value)
      jsonContent.value = JSON.stringify(parsed, null, 2)
      toast.add({
        severity: 'success',
        summary: t('functions.jsonFormatted'),
        detail: t('functions.jsonFormattedDesc'),
        life: 3000,
      })
    } catch {
      toast.add({
        severity: 'error',
        summary: t('functions.errorFormat'),
        detail: t('functions.errorFormatDesc'),
        life: 3000,
      })
    }
  }
}

const saveFunctions = async () => {
  if (!validateJson(jsonContent.value)) {
    toast.add({
      severity: 'error',
      summary: t('functions.validationError'),
      detail: jsonError.value,
      life: 5000,
    })
    return
  }

  isSaving.value = true

  try {
    const parsedJson = JSON.parse(jsonContent.value)

    let functionsArray: Record<string, unknown>[]

    if (Array.isArray(parsedJson)) {
      functionsArray = parsedJson
    } else if (parsedJson.functions && Array.isArray(parsedJson.functions)) {
      functionsArray = parsedJson.functions
    } else {
      throw new Error(t('functions.jsonMustBeArray'))
    }

    for (const func of functionsArray) {
      if (!func.name || !func.description || !func.type) {
        throw new Error(t('functions.eachFunctionRequired'))
      }
    }

    await updateAssistantProfile({
      assistant_name: assistantProfile.value?.assistant_name,
      functions: jsonContent.value,
    })

    toast.add({
      severity: 'success',
      summary: t('functions.functionsSaved'),
      detail: t('functions.functionsSavedDesc'),
      life: 3000,
    })

    isEditing.value = false
    editorMode.value = 'json'
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : t('common.unknownError')
    toast.add({
      severity: 'error',
      summary: t('functions.errorSave'),
      detail: errorMessage,
      life: 5000,
    })
  } finally {
    isSaving.value = false
  }
}

const toggleEdit = () => {
  if (isEditing.value) {
    if (assistantProfile.value?.functions && assistantProfile.value.functions.trim() !== '') {
      jsonContent.value = assistantProfile.value.functions
    } else {
      jsonContent.value = JSON.stringify(sampleJson, null, 2)
    }
    jsonError.value = ''
    editorMode.value = 'json'
  }
  isEditing.value = !isEditing.value
}

const clearJson = () => {
  jsonContent.value = ''
  jsonError.value = ''
  toast.add({
    severity: 'info',
    summary: t('functions.jsonCleared'),
    detail: t('functions.jsonClearedDesc'),
    life: 3000,
  })
}

const restoreSample = () => {
  jsonContent.value = JSON.stringify(sampleJson, null, 2)
  jsonError.value = ''
  toast.add({
    severity: 'info',
    summary: t('functions.jsonRestored'),
    detail: t('functions.jsonRestoredDesc'),
    life: 3000,
  })
}

const parseJsonToWorkflow = (): WorkflowFunction | null => {
  const workflows = availableWorkflows.value

  if (workflows.length === 0) {
    return null
  }

  if (selectedWorkflowIndex.value >= workflows.length) {
    selectedWorkflowIndex.value = 0
  }

  return workflows[selectedWorkflowIndex.value]
}

const toggleEditorMode = () => {
  if (editorMode.value === 'json') {
    currentWorkflow.value = parseJsonToWorkflow()
    if (currentWorkflow.value) {
      editorMode.value = 'visual'
    } else {
      toast.add({
        severity: 'warn',
        summary: t('functions.invalidWorkflow'),
        detail: t('functions.invalidWorkflowDesc'),
        life: 5000,
      })
    }
  } else {
    editorMode.value = 'json'
  }
}

const toggleWorkflowVisual = () => {
  if (showWorkflowVisual.value) {
    showWorkflowVisual.value = false
  } else {
    currentWorkflow.value = parseJsonToWorkflow()
    if (currentWorkflow.value) {
      showWorkflowVisual.value = true
    } else {
      toast.add({
        severity: 'warn',
        summary: t('functions.noWorkflow'),
        detail: t('functions.noWorkflowDesc'),
        life: 3000,
      })
    }
  }
}

const handleWorkflowSave = async (workflow: WorkflowFunction) => {
  jsonContent.value = JSON.stringify([workflow], null, 2)
  await saveFunctions()
}

const handleWorkflowUpdate = (workflow: WorkflowFunction) => {
  jsonContent.value = JSON.stringify([workflow], null, 2)
  toast.add({
    severity: 'success',
    summary: t('functions.workflowExported'),
    detail: t('functions.workflowExportedDesc'),
    life: 3000,
  })
}

const handleWorkflowChange = () => {
  currentWorkflow.value = parseJsonToWorkflow()
}

const getFunctionIcon = (type: string): string => {
  switch (type) {
    case 'workflow':
      return 'pi pi-sitemap'
    case 'http':
      return 'pi pi-globe'
    case 'function':
      return 'pi pi-cog'
    default:
      return 'pi pi-code'
  }
}

const openWorkflowForCard = (fn: Record<string, unknown>) => {
  const idx = availableWorkflows.value.findIndex((w) => w.name === fn.name)
  if (idx >= 0) {
    selectedWorkflowIndex.value = idx
    currentWorkflow.value = parseJsonToWorkflow()
    showWorkflowVisual.value = true
  }
}
</script>

<template>
  <div class="functions-container">
    <!-- Header Section -->
    <div class="header-section">
      <div class="functions-header">
        <div class="header-content">
          <div class="icon-wrapper">
            <i class="pi pi-code"></i>
          </div>
          <div class="title-section">
            <h1 class="page-title">{{ t('functions.title') }}</h1>
            <p class="page-subtitle">
              {{ t('functions.subtitle') }}
            </p>
          </div>
        </div>
        <div class="header-actions">
          <Button
            v-tooltip.bottom="t('functions.openGuide')"
            icon="pi pi-book"
            size="small"
            severity="help"
            text
            rounded
            class="header-icon-btn"
            @click="showGuideModal = true"
          />

          <template v-if="!isEditing">
            <Button
              v-if="hasWorkflow()"
              v-tooltip.bottom="
                showWorkflowVisual ? t('functions.hideWorkflow') : t('functions.viewWorkflow')
              "
              :icon="showWorkflowVisual ? 'pi pi-eye-slash' : 'pi pi-sitemap'"
              size="small"
              severity="secondary"
              text
              rounded
              class="header-icon-btn"
              @click="toggleWorkflowVisual"
            />
            <Button
              v-tooltip.bottom="t('functions.editFunctions')"
              icon="pi pi-pencil"
              size="small"
              rounded
              class="header-edit-btn"
              @click="toggleEdit"
            />
          </template>
        </div>
      </div>
    </div>

    <!-- Editing Banner -->
    <div v-if="isEditing" class="editing-banner">
      <div class="banner-left">
        <span class="banner-dot"></span>
        <span class="banner-label">{{ t('functions.editMode') }}</span>
        <div class="banner-tools">
          <Button
            v-tooltip.bottom="t('functions.formatJson')"
            icon="pi pi-refresh"
            size="small"
            text
            @click="formatJson"
          />
          <Button
            v-tooltip.bottom="t('functions.clearEditor')"
            icon="pi pi-trash"
            size="small"
            text
            severity="danger"
            @click="clearJson"
          />
          <Button
            v-tooltip.bottom="t('functions.restoreSample')"
            icon="pi pi-undo"
            size="small"
            text
            @click="restoreSample"
          />
          <Dropdown
            v-if="availableWorkflows.length > 1"
            v-model="selectedWorkflowIndex"
            :options="
              availableWorkflows.map((w: WorkflowFunction, idx: number) => ({
                label: w.name,
                value: idx,
              }))
            "
            option-label="label"
            option-value="value"
            :placeholder="t('functions.selectWorkflow')"
            class="workflow-selector"
            @change="handleWorkflowChange"
          />
        </div>
      </div>
      <div class="banner-right">
        <Button
          v-if="hasWorkflow()"
          v-tooltip.bottom="
            editorMode === 'json' ? t('functions.switchToVisual') : t('functions.switchToJson')
          "
          :icon="editorMode === 'json' ? 'pi pi-sitemap' : 'pi pi-code'"
          size="small"
          severity="info"
          @click="toggleEditorMode"
        />
        <Button
          v-tooltip.bottom="t('functions.cancelEdit')"
          icon="pi pi-times"
          size="small"
          severity="secondary"
          @click="toggleEdit"
        />
        <Button
          v-tooltip.bottom="t('functions.saveFunctions')"
          icon="pi pi-save"
          size="small"
          :loading="isSaving"
          :disabled="!!jsonError"
          @click="saveFunctions"
        />
      </div>
    </div>

    <!-- Functions Summary Panel (readonly, has functions) -->
    <div v-if="!isEditing && allFunctions.length > 0" class="functions-summary">
      <div class="summary-header">
        <span class="summary-title">
          <i class="pi pi-list"></i>
          Funciones configuradas
          <span class="summary-count">{{ allFunctions.length }}</span>
        </span>
        <Button
          v-tooltip.bottom="t('functions.editFunctions')"
          icon="pi pi-pencil"
          size="small"
          text
          rounded
          class="summary-edit-btn"
          @click="toggleEdit"
        />
      </div>
      <div class="functions-grid">
        <div
          v-for="fn in allFunctions"
          :key="fn.name"
          class="function-card"
          :class="{
            'type-border-workflow': fn.type === 'workflow',
            'type-border-http': fn.type === 'http',
          }"
        >
          <div class="function-card-header">
            <div class="function-name-row">
              <i :class="getFunctionIcon(fn.type)" class="function-icon"></i>
              <span class="function-name">{{ fn.name }}</span>
            </div>
            <span
              class="function-type-badge"
              :class="{
                'type-workflow': fn.type === 'workflow',
                'type-http': fn.type === 'http',
                'type-default': fn.type !== 'workflow' && fn.type !== 'http',
              }"
              >{{ fn.type }}</span
            >
          </div>
          <p class="function-desc">{{ fn.description || t('common.description') }}</p>
          <div class="function-footer">
            <div v-if="fn.input_params && fn.input_params.length" class="function-meta">
              <i class="pi pi-sliders-h"></i>
              <span
                >{{ fn.input_params.length }} parámetro{{
                  fn.input_params.length !== 1 ? 's' : ''
                }}</span
              >
            </div>
            <div v-else-if="fn.steps && fn.steps.length" class="function-meta">
              <i class="pi pi-share-alt"></i>
              <span>{{ fn.steps.length }} paso{{ fn.steps.length !== 1 ? 's' : '' }}</span>
            </div>
            <div v-else-if="fn.keywords && fn.keywords.length" class="function-meta">
              <i class="pi pi-tag"></i>
              <span>{{ fn.keywords.slice(0, 3).join(', ') }}</span>
            </div>
            <Button
              v-if="fn.type === 'workflow'"
              v-tooltip.bottom="t('functions.viewWorkflow')"
              icon="pi pi-sitemap"
              size="small"
              text
              class="card-workflow-btn"
              @click.stop="openWorkflowForCard(fn)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State (readonly, no functions) -->
    <Card v-else-if="!isEditing && allFunctions.length === 0" class="empty-state-card">
      <template #content>
        <div class="empty-state">
          <div class="empty-illustration">
            <div class="empty-icon-ring">
              <i class="pi pi-code"></i>
            </div>
            <div class="empty-icon-ring empty-ring-2">
              <i class="pi pi-cog"></i>
            </div>
            <div class="empty-icon-ring empty-ring-3">
              <i class="pi pi-sitemap"></i>
            </div>
          </div>
          <div class="empty-text">
            <h3 class="empty-title">{{ t('functions.noWorkflow') }}</h3>
            <p class="empty-desc">
              {{ t('functions.noWorkflowDesc') }}
            </p>
            <div class="empty-actions">
              <Button
                :label="t('functions.editFunctions')"
                icon="pi pi-plus"
                class="edit-button"
                @click="toggleEdit"
              />
              <Button
                :label="t('functions.openGuide')"
                icon="pi pi-book"
                severity="secondary"
                text
                @click="showGuideModal = true"
              />
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Visual Workflow Viewer (readonly, toggled) -->
    <WorkflowEditor
      v-if="!isEditing && showWorkflowVisual && currentWorkflow"
      :workflow="currentWorkflow"
      :readonly="true"
    />

    <!-- Visual Workflow Editor (editing, visual mode) -->
    <WorkflowEditor
      v-else-if="isEditing && editorMode === 'visual'"
      :workflow="currentWorkflow!"
      :readonly="false"
      @save="handleWorkflowSave"
      @update="handleWorkflowUpdate"
    />

    <!-- JSON Editor Card (editing, json mode only) -->
    <Card v-if="isEditing && editorMode === 'json'" class="editor-card">
      <template #content>
        <div class="editor-section">
          <div class="editor-header">
            <label for="json-editor" class="editor-label">
              <i class="pi pi-file-edit"></i>
              Configuración JSON
            </label>
          </div>

          <div class="editor-wrapper">
            <Textarea
              id="json-editor"
              v-model="jsonContent"
              :disabled="!isEditing"
              :rows="25"
              class="json-editor"
              :class="{
                'editor-error': jsonError,
              }"
              :placeholder="t('functions.subtitle')"
              @input="validateJson(jsonContent)"
            />

            <div v-if="jsonError" class="error-message">
              <i class="pi pi-exclamation-triangle"></i>
              <span>{{ jsonError }}</span>
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>

  <!-- Workflow Guide Modal -->
  <WorkflowGuideModal v-model:visible="showGuideModal" />

  <Toast position="top-right" />
</template>

<style scoped>
.functions-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem;
  min-height: 100vh;
  background: var(--do-bg);
}

/* Header Section */
.header-section {
  margin-bottom: 1.25rem;
}

.functions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.04);
  padding: 0.875rem 1.25rem;
  border-radius: 0.875rem;
  border: 1px solid var(--do-border-light);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 0.875rem;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: var(--do-blue);
  flex-shrink: 0;
}

.title-section {
  flex: 1;
}

.page-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0 0 0.1rem 0;
  background: linear-gradient(135deg, var(--do-text) 0%, var(--do-text-secondary) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.3;
}

.page-subtitle {
  font-size: 0.8rem;
  color: var(--do-text-muted);
  margin: 0;
  font-weight: 400;
  line-height: 1.3;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.header-icon-btn {
  width: 2rem;
  height: 2rem;
}

.header-edit-btn {
  background: var(--gradient-primary);
  border: none;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    transform 0.15s,
    box-shadow 0.15s;
  box-shadow: var(--shadow-primary);
}

.header-edit-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px var(--shadow-medium);
}

/* Editing Banner */
.editing-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(var(--color-primary-rgb, 99, 102, 241), 0.08);
  border: 1px solid rgba(var(--color-primary-rgb, 99, 102, 241), 0.2);
  border-radius: 0.75rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.banner-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.banner-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.banner-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success, #22c55e);
  animation: pulse 2s infinite;
  flex-shrink: 0;
}

.banner-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--do-text);
}

.banner-tools {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

/* Workflow Selector (inside banner) */
:deep(.workflow-selector) {
  min-width: 180px;
  border-radius: 0.5rem;
  border: 1px solid var(--do-border-light);
  background: rgba(255, 255, 255, 0.04);
  transition: all 0.2s ease;
  height: 2rem;
}

:deep(.workflow-selector:hover) {
  border-color: var(--color-primary);
}

:deep(.workflow-selector .p-dropdown-label) {
  padding: 0.35rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--vt-c-gray-700);
}

:deep(.workflow-selector .p-dropdown-trigger) {
  color: var(--color-primary);
  width: 2rem;
}

/* Functions Summary Panel */
.functions-summary {
  margin-bottom: 1.25rem;
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.875rem;
}

.summary-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--do-text-secondary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.summary-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.35rem;
  height: 1.35rem;
  border-radius: 50%;
  background: var(--gradient-primary);
  color: white;
  font-size: 0.7rem;
  font-weight: 700;
}

.summary-edit-btn {
  opacity: 0.7;
  transition: opacity 0.15s;
}

.summary-edit-btn:hover {
  opacity: 1;
}

.functions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.875rem;
}

/* Function Cards */
.function-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--do-border-light);
  border-left: 3px solid var(--do-border-light);
  border-radius: 0.75rem;
  padding: 0.875rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  transition:
    transform 0.15s,
    box-shadow 0.15s;
  cursor: default;
}

.function-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.function-card.type-border-workflow {
  border-left-color: var(--color-primary, #6366f1);
}

.function-card.type-border-http {
  border-left-color: var(--color-info, #0ea5e9);
}

.function-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.function-name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.function-icon {
  color: var(--color-primary);
  font-size: 0.875rem;
  flex-shrink: 0;
}

.function-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--do-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.function-type-badge {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.175rem 0.5rem;
  border-radius: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}

.type-workflow {
  background: var(--gradient-primary);
  color: white;
}

.type-http {
  background: var(--gradient-info);
  color: white;
}

.type-default {
  background: rgba(255, 255, 255, 0.1);
  color: var(--do-text-muted);
}

.function-desc {
  font-size: 0.82rem;
  color: var(--do-text-muted);
  line-height: 1.4;
  margin: 0;
}

.function-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 0.125rem;
}

.function-meta {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: var(--do-text-muted);
}

.function-meta i {
  font-size: 0.7rem;
  color: var(--color-primary);
}

:deep(.card-workflow-btn) {
  padding: 0.2rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 0.4rem;
  color: var(--color-primary);
  opacity: 0.8;
  transition: opacity 0.15s;
}

:deep(.card-workflow-btn:hover) {
  opacity: 1;
}

/* Empty State */
.empty-state-card {
  margin-bottom: 1.5rem;
  border-radius: 1rem;
  overflow: hidden;
  border: 1px solid var(--do-border-light);
  background: rgba(255, 255, 255, 0.02);
}

:deep(.empty-state-card .p-card-content) {
  padding: 0;
}

.empty-state {
  display: grid;
  grid-template-columns: 220px 1fr;
  align-items: center;
  padding: 3rem 2.5rem;
  gap: 2.5rem;
}

.empty-illustration {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  height: 140px;
}

.empty-icon-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid var(--do-border-light);
  background: rgba(255, 255, 255, 0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--do-text-muted);
}

.empty-icon-ring:nth-child(1) {
  width: 72px;
  height: 72px;
  font-size: 1.75rem;
  color: var(--color-primary);
  background: rgba(var(--color-primary-rgb, 99, 102, 241), 0.08);
  border-color: rgba(var(--color-primary-rgb, 99, 102, 241), 0.2);
  z-index: 3;
}

.empty-ring-2 {
  width: 100px;
  height: 100px;
  font-size: 1rem;
  color: var(--do-text-muted);
  z-index: 2;
  transform: translate(28px, -20px);
}

.empty-ring-3 {
  width: 56px;
  height: 56px;
  font-size: 0.875rem;
  z-index: 2;
  transform: translate(-30px, 24px);
}

.empty-text {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.empty-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0;
}

.empty-desc {
  font-size: 0.875rem;
  color: var(--do-text-muted);
  max-width: 440px;
  line-height: 1.65;
  margin: 0;
}

.empty-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 0.25rem;
}

:deep(.edit-button) {
  background: var(--gradient-success);
  border: none;
  border-radius: 0.625rem;
  font-weight: 600;
  transition: all 0.2s ease;
  box-shadow: var(--shadow-success);
}

:deep(.edit-button:hover) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px var(--shadow-medium);
}

/* Editor Card */
.editor-card {
  margin-bottom: 1.5rem;
  border-radius: 1rem;
  overflow: hidden;
  border: 1px solid var(--do-border-light);
  transition: box-shadow 0.2s ease;
}

.editor-card:hover {
  box-shadow: 0 8px 32px var(--shadow-light);
}

:deep(.editor-card .p-card-content) {
  padding: 0;
}

/* Editor Section */
.editor-section {
  padding: 1.5rem;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.editor-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--vt-c-gray-700);
}

.editor-label i {
  color: var(--color-primary);
  font-size: 1rem;
}

/* Editor Wrapper */
.editor-wrapper {
  position: relative;
}

:deep(.json-editor) {
  width: 100%;
  border: 2px solid var(--do-border-light);
  border-radius: 0.75rem;
  padding: 1.25rem;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  background: var(--do-text);
  color: var(--do-border-light);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
  resize: vertical;
  min-height: 600px;
}

:deep(.json-editor:focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--vt-c-gray-200);
  outline: none;
}

:deep(.json-editor.editor-error) {
  border-color: var(--color-danger);
  box-shadow: 0 0 0 3px var(--vt-c-danger-lighter);
}

/* Error Message */
.error-message {
  margin-top: 0.875rem;
  padding: 0.875rem 1rem;
  background: var(--vt-c-danger-lighter);
  border: 1px solid var(--vt-c-danger-light);
  border-radius: 0.625rem;
  color: var(--color-danger-dark);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  font-size: 0.875rem;
}

.error-message i {
  font-size: 1rem;
  flex-shrink: 0;
}

/* Pulse animation */
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}

/* Responsive Design */
@media (max-width: 768px) {
  .functions-container {
    padding: 1rem;
  }

  .functions-header {
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .editing-banner {
    flex-direction: column;
    align-items: stretch;
  }

  .banner-right {
    justify-content: flex-end;
  }

  .functions-grid {
    grid-template-columns: 1fr;
  }

  .empty-state {
    grid-template-columns: 1fr;
    text-align: center;
    padding: 2.5rem 1.5rem;
    gap: 1.5rem;
  }

  .empty-illustration {
    height: 100px;
  }

  .empty-actions {
    justify-content: center;
  }

  .editor-section {
    padding: 1.25rem;
  }

  :deep(.json-editor) {
    font-size: 0.8rem;
    padding: 1rem;
    min-height: 400px;
  }
}

@media (max-width: 480px) {
  .functions-container {
    padding: 0.75rem;
  }

  .page-title {
    font-size: 1rem;
  }

  .page-subtitle {
    display: none;
  }

  .editor-section {
    padding: 1rem;
  }

  :deep(.json-editor) {
    padding: 0.75rem;
    min-height: 300px;
  }
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
  .editor-card,
  :deep(.edit-button),
  .function-card,
  .header-edit-btn {
    transition: none;
  }

  .editor-card:hover,
  :deep(.edit-button:hover),
  .function-card:hover,
  .header-edit-btn:hover {
    transform: none;
  }

  .banner-dot {
    animation: none;
  }
}
</style>
