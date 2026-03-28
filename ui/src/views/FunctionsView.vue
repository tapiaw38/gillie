<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Toast from 'primevue/toast'
import Dropdown from 'primevue/dropdown'
import { useToast } from 'primevue/usetoast'
import { useAssistant } from '@/composables/useAssistant'
import WorkflowEditor from '@/components/workflow/WorkflowEditor.vue'
import WorkflowGuideModal from '@/components/workflow/WorkflowGuideModal.vue'
import type { WorkflowFunction } from '@/types/workflow.types'

const toast = useToast()

const { getAssistantProfile, updateAssistantProfile, assistantProfile } = useAssistant()

const jsonContent = ref('')
const isEditing = ref(false)
const isSaving = ref(false)
const jsonError = ref('')
const editorMode = ref<'json' | 'visual'>('json')
const currentWorkflow = ref<WorkflowFunction | null>(null)
const showGuideModal = ref(false)
const selectedWorkflowIndex = ref(0)

// Readonly mode toggles — no auto-switch on mount
const showJsonPanel = ref(false)
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

// All parsed functions regardless of type
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

// Only workflow-type functions for visual editor
const availableWorkflows = computed(() => {
  try {
    const parsed = JSON.parse(jsonContent.value)
    if (Array.isArray(parsed)) {
      return parsed.filter((f) => f.type === 'workflow')
    } else if (parsed.functions && Array.isArray(parsed.functions)) {
      return parsed.functions.filter((f: { type: string }) => f.type === 'workflow')
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
          jsonError.value = 'Cada función debe tener: name, description y type'
          return false
        }
      }
    } else if (parsed.functions && Array.isArray(parsed.functions)) {
      for (const func of parsed.functions) {
        if (!func.name || !func.description || !func.type) {
          jsonError.value = 'Cada función debe tener: name, description y type'
          return false
        }
      }
    } else {
      jsonError.value =
        'El JSON debe ser un array de funciones o tener un campo "functions" con array'
      return false
    }

    jsonError.value = ''
    return true
  } catch (error) {
    jsonError.value = `Error de sintaxis JSON: ${
      error instanceof Error ? error.message : 'Error desconocido'
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
        summary: 'JSON formateado',
        detail: 'El JSON se ha formateado correctamente',
        life: 3000,
      })
    } catch {
      toast.add({
        severity: 'error',
        summary: 'Error al formatear',
        detail: 'No se pudo formatear el JSON',
        life: 3000,
      })
    }
  }
}

const saveFunctions = async () => {
  if (!validateJson(jsonContent.value)) {
    toast.add({
      severity: 'error',
      summary: 'Error de validación',
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
      throw new Error(
        'El JSON debe ser un array de funciones o tener un campo "functions" con array',
      )
    }

    for (const func of functionsArray) {
      if (!func.name || !func.description || !func.type) {
        throw new Error('Cada función debe tener: name, description y type')
      }
    }

    await updateAssistantProfile({
      assistant_name: assistantProfile.value?.assistant_name,
      functions: jsonContent.value,
    })

    toast.add({
      severity: 'success',
      summary: 'Funciones guardadas',
      detail: 'Las funciones se han guardado correctamente',
      life: 3000,
    })

    isEditing.value = false
    editorMode.value = 'json'
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Error desconocido al guardar'
    toast.add({
      severity: 'error',
      summary: 'Error al guardar',
      detail: errorMessage,
      life: 5000,
    })
  } finally {
    isSaving.value = false
  }
}

const toggleEdit = () => {
  if (isEditing.value) {
    // Cancelling — restore from profile or sample
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
    summary: 'JSON limpiado',
    detail: 'El editor se ha limpiado',
    life: 3000,
  })
}

const restoreSample = () => {
  jsonContent.value = JSON.stringify(sampleJson, null, 2)
  jsonError.value = ''
  toast.add({
    severity: 'info',
    summary: 'JSON restaurado',
    detail: 'Se ha restaurado el JSON de ejemplo',
    life: 3000,
  })
}

// Parse JSON to workflow for visual editor
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

// Toggle between JSON and Visual editor (editing mode)
const toggleEditorMode = () => {
  if (editorMode.value === 'json') {
    currentWorkflow.value = parseJsonToWorkflow()
    if (currentWorkflow.value) {
      editorMode.value = 'visual'
    } else {
      toast.add({
        severity: 'warn',
        summary: 'Workflow Inválido',
        detail:
          'Por favor, asegúrate de que tu JSON contenga un workflow válido antes de cambiar al modo visual',
        life: 5000,
      })
    }
  } else {
    editorMode.value = 'json'
  }
}

// Toggle workflow visual in readonly mode
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
        summary: 'Sin Workflow',
        detail: 'No se detectó un workflow válido en el JSON',
        life: 3000,
      })
    }
  }
}

// Handle workflow save from visual editor
const handleWorkflowSave = async (workflow: WorkflowFunction) => {
  jsonContent.value = JSON.stringify([workflow], null, 2)
  await saveFunctions()
}

// Handle workflow update from visual editor (export to JSON without saving)
const handleWorkflowUpdate = (workflow: WorkflowFunction) => {
  jsonContent.value = JSON.stringify([workflow], null, 2)
  toast.add({
    severity: 'success',
    summary: 'Workflow Exportado',
    detail:
      'El workflow visual se ha convertido a JSON. Usa "Guardar Funciones" para persistir los cambios.',
    life: 3000,
  })
}

// Handle workflow selection change
const handleWorkflowChange = () => {
  currentWorkflow.value = parseJsonToWorkflow()
}

// Returns icon class based on function type
const getFunctionIcon = (type: string): string => {
  switch (type) {
    case 'workflow': return 'pi pi-sitemap'
    case 'http': return 'pi pi-globe'
    case 'function': return 'pi pi-cog'
    default: return 'pi pi-code'
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
            <h1 class="page-title">Editor de Funciones</h1>
            <p class="page-subtitle">
              Define funciones personalizadas para tu asistente en formato JSON
            </p>
          </div>
        </div>
        <div class="header-actions">
          <!-- Guide Button (always visible) -->
          <Button
            label="Guía Rápida"
            icon="pi pi-book"
            class="guide-button"
            severity="help"
            @click="showGuideModal = true"
          />

          <!-- Readonly mode actions -->
          <template v-if="!isEditing">
            <Button
              v-if="hasWorkflow()"
              :label="showWorkflowVisual ? 'Ocultar Workflow' : 'Ver Workflow'"
              :icon="showWorkflowVisual ? 'pi pi-eye-slash' : 'pi pi-sitemap'"
              class="view-toggle-button"
              severity="secondary"
              @click="toggleWorkflowVisual"
            />
            <Button
              label="Editar"
              icon="pi pi-pencil"
              class="edit-button"
              @click="toggleEdit"
            />
          </template>

          <!-- Editing mode actions -->
          <template v-else>
            <!-- Workflow selector (multiple workflows in JSON) -->
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
              placeholder="Selecciona Workflow"
              class="workflow-selector"
              @change="handleWorkflowChange"
            />
            <Button
              v-if="hasWorkflow()"
              :label="editorMode === 'json' ? 'Editor Visual' : 'Editor JSON'"
              :icon="editorMode === 'json' ? 'pi pi-sitemap' : 'pi pi-code'"
              class="mode-toggle-button"
              severity="info"
              @click="toggleEditorMode"
            />
            <Button
              label="Cancelar"
              icon="pi pi-times"
              severity="secondary"
              class="cancel-button"
              @click="toggleEdit"
            />
          </template>
        </div>
      </div>
    </div>

    <!-- Functions Summary Panel (readonly, has functions) -->
    <div
      v-if="!isEditing && allFunctions.length > 0"
      class="functions-summary"
    >
      <div class="summary-header">
        <span class="summary-title">
          <i class="pi pi-list"></i>
          Funciones configuradas
          <span class="summary-count">{{ allFunctions.length }}</span>
        </span>
        <Button
          :label="showJsonPanel ? 'Ocultar JSON' : 'Ver JSON'"
          :icon="showJsonPanel ? 'pi pi-eye-slash' : 'pi pi-code'"
          size="small"
          class="json-toggle-button"
          severity="secondary"
          @click="showJsonPanel = !showJsonPanel"
        />
      </div>
      <div class="functions-grid">
        <div
          v-for="fn in allFunctions"
          :key="fn.name"
          class="function-card"
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
            >{{ fn.type }}</span>
          </div>
          <p class="function-desc">{{ fn.description || 'Sin descripción' }}</p>
          <div v-if="fn.steps && fn.steps.length" class="function-meta">
            <i class="pi pi-share-alt"></i>
            <span>{{ fn.steps.length }} paso{{ fn.steps.length !== 1 ? 's' : '' }}</span>
          </div>
          <div v-else-if="fn.keywords && fn.keywords.length" class="function-meta">
            <i class="pi pi-tag"></i>
            <span>{{ fn.keywords.slice(0, 3).join(', ') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State (readonly, no functions) -->
    <Card
      v-else-if="!isEditing && allFunctions.length === 0"
      class="empty-state-card"
    >
      <template #content>
        <div class="empty-state">
          <div class="empty-icon">
            <i class="pi pi-code"></i>
          </div>
          <h3 class="empty-title">Sin funciones configuradas</h3>
          <p class="empty-desc">
            Aún no has definido ninguna función para tu asistente. Crea tu primera función para extender sus capacidades.
          </p>
          <Button
            label="Crear primera función"
            icon="pi pi-plus"
            class="edit-button"
            @click="toggleEdit"
          />
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

    <!-- JSON Editor Card (editing, json mode) or JSON Panel (readonly toggle) -->
    <Card
      v-if="(isEditing && editorMode === 'json') || (!isEditing && showJsonPanel && !showWorkflowVisual)"
      class="editor-card"
    >
      <template #content>
        <!-- Toolbar (only visible when editing) -->
        <div v-if="isEditing" class="editor-toolbar">
          <div class="toolbar-section">
            <div class="toolbar-title">
              <i class="pi pi-wrench"></i>
              <span>Herramientas de Edición</span>
            </div>
            <div class="toolbar-actions">
              <Button
                label="Formatear"
                icon="pi pi-refresh"
                class="toolbar-button format-button"
                size="small"
                @click="formatJson"
              />
              <Button
                label="Limpiar"
                icon="pi pi-trash"
                class="toolbar-button clear-button"
                size="small"
                @click="clearJson"
              />
              <Button
                label="Restaurar"
                icon="pi pi-undo"
                class="toolbar-button restore-button"
                size="small"
                @click="restoreSample"
              />
            </div>
          </div>
          <div class="editing-indicator">
            <i class="pi pi-circle-fill editing-dot"></i>
            <span>Modo de edición activo</span>
          </div>
        </div>

        <!-- JSON Editor -->
        <div class="editor-section">
          <div class="editor-header">
            <label for="json-editor" class="editor-label">
              <i class="pi pi-file-edit"></i>
              Configuración JSON
            </label>
            <div v-if="!isEditing" class="readonly-badge">
              <i class="pi pi-lock"></i>
              Solo lectura
            </div>
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
                'editor-readonly': !isEditing,
              }"
              placeholder="Ingresa tu configuración JSON aquí..."
              @input="validateJson(jsonContent)"
            />

            <div v-if="jsonError" class="error-message">
              <i class="pi pi-exclamation-triangle"></i>
              <span>{{ jsonError }}</span>
            </div>
          </div>

          <!-- Save Button (only visible when editing) -->
          <div v-if="isEditing" class="save-section">
            <Button
              label="Guardar Funciones"
              icon="pi pi-save"
              class="save-button"
              :loading="isSaving"
              :disabled="!!jsonError"
              @click="saveFunctions"
            />
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
  padding: 2rem;
  min-height: 100vh;
  background: var(--do-bg);
}

/* Header Section */
.header-section {
  margin-bottom: 2rem;
}

.functions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.04);
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 4px 20px var(--shadow-light);
  border: 1px solid var(--do-border-light);
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
  flex-shrink: 0;
}

.title-section {
  flex: 1;
}

.page-title {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0 0 0.5rem 0;
  background: linear-gradient(135deg, var(--do-text) 0%, var(--do-text-secondary) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-subtitle {
  font-size: 1.125rem;
  color: var(--do-text-muted);
  margin: 0;
  font-weight: 400;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

/* Functions Summary Panel */
.functions-summary {
  margin-bottom: 1.5rem;
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.summary-title {
  font-size: 1rem;
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
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  background: var(--gradient-primary);
  color: white;
  font-size: 0.75rem;
  font-weight: 700;
}

.functions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.function-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--do-border-light);
  border-radius: 0.75rem;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.function-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 4px 20px var(--shadow-primary);
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
  font-size: 0.9rem;
  flex-shrink: 0;
}

.function-name {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--do-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.function-type-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
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
  font-size: 0.85rem;
  color: var(--do-text-muted);
  line-height: 1.4;
  margin: 0;
}

.function-meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--do-text-muted);
  margin-top: 0.25rem;
}

.function-meta i {
  font-size: 0.75rem;
  color: var(--color-primary);
}

/* JSON toggle button */
:deep(.json-toggle-button) {
  border-radius: 0.5rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

/* Empty State */
.empty-state-card {
  margin-bottom: 2rem;
  border-radius: 1rem;
  overflow: hidden;
  border: 1px solid var(--do-border-light);
  background: rgba(255, 255, 255, 0.02);
}

:deep(.empty-state-card .p-card-content) {
  padding: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 4rem 2rem;
  gap: 1rem;
}

.empty-icon {
  width: 5rem;
  height: 5rem;
  border-radius: 1.25rem;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--do-border-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: var(--do-text-muted);
  margin-bottom: 0.5rem;
}

.empty-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--do-text);
  margin: 0;
}

.empty-desc {
  font-size: 0.9rem;
  color: var(--do-text-muted);
  max-width: 420px;
  line-height: 1.6;
  margin: 0 0 0.5rem 0;
}

/* Button styles */
:deep(.edit-button) {
  background: var(--gradient-success);
  border: none;
  border-radius: 0.75rem;
  padding: 0.875rem 1.5rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-success);
}

:deep(.edit-button:hover) {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px var(--shadow-medium);
}

:deep(.cancel-button) {
  border-radius: 0.75rem;
  padding: 0.875rem 1.5rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

:deep(.mode-toggle-button) {
  background: var(--gradient-primary);
  border: none;
  border-radius: 0.75rem;
  padding: 0.875rem 1.5rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-primary);
}

:deep(.mode-toggle-button:hover) {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px var(--shadow-medium);
}

:deep(.view-toggle-button) {
  background: linear-gradient(135deg, var(--do-text-muted) 0%, var(--do-text-secondary) 100%);
  border: none;
  border-radius: 0.75rem;
  padding: 0.875rem 1.5rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 20px var(--shadow-medium);
}

:deep(.view-toggle-button:hover) {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px var(--shadow-medium);
}

:deep(.guide-button) {
  background: var(--gradient-primary);
  border: none;
  border-radius: 0.75rem;
  padding: 0.875rem 1.5rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-primary);
}

:deep(.guide-button:hover) {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px var(--shadow-medium);
}

/* Workflow Selector */
:deep(.workflow-selector) {
  min-width: 250px;
  border-radius: 0.75rem;
  border: 2px solid var(--do-border-light);
  background: rgba(255, 255, 255, 0.04);
  transition: all 0.3s ease;
}

:deep(.workflow-selector:hover) {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-primary);
}

:deep(.workflow-selector .p-dropdown-label) {
  padding: 0.75rem 1rem;
  font-weight: 600;
  color: var(--vt-c-gray-700);
}

:deep(.workflow-selector .p-dropdown-trigger) {
  color: var(--color-primary);
}

/* Editor Card */
.editor-card {
  margin-bottom: 2rem;
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 40px var(--shadow-light);
  border: 1px solid var(--do-border-light);
  transition: all 0.3s ease;
}

.editor-card:hover {
  box-shadow: 0 20px 60px var(--shadow-medium);
  transform: translateY(-2px);
}

:deep(.editor-card .p-card-content) {
  padding: 0;
}

/* Editor Toolbar */
.editor-toolbar {
  background: linear-gradient(135deg, var(--vt-c-gray-100) 0%, var(--do-border-light) 100%);
  padding: 1.5rem 2rem;
  border-bottom: 1px solid var(--do-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.toolbar-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--vt-c-gray-700);
}

.toolbar-title i {
  color: var(--color-primary);
  font-size: 1.125rem;
}

.toolbar-actions {
  display: flex;
  gap: 0.75rem;
}

:deep(.toolbar-button) {
  border-radius: 0.5rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

:deep(.format-button) {
  background: var(--gradient-info);
  border: none;
  color: white;
}

:deep(.clear-button) {
  background: var(--gradient-warning);
  border: none;
  color: white;
}

:deep(.restore-button) {
  background: linear-gradient(135deg, var(--do-text-muted) 0%, var(--vt-c-gray-700) 100%);
  border: none;
  color: white;
}

:deep(.toolbar-button:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 20px var(--shadow-medium);
}

.editing-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--color-success-dark);
  font-weight: 500;
  font-size: 0.875rem;
}

.editing-dot {
  color: var(--color-success);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* Editor Section */
.editor-section {
  padding: 2rem;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.editor-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--vt-c-gray-700);
}

.editor-label i {
  color: var(--color-primary);
  font-size: 1.25rem;
}

.readonly-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--vt-c-gray-100);
  border: 1px solid var(--do-border-light);
  border-radius: 1rem;
  color: var(--do-text-muted);
  font-size: 0.875rem;
  font-weight: 500;
}

.readonly-badge i {
  color: var(--vt-c-gray-400);
}

/* Editor Wrapper */
.editor-wrapper {
  position: relative;
  margin-bottom: 2rem;
}

:deep(.json-editor) {
  width: 100%;
  border: 2px solid var(--do-border-light);
  border-radius: 0.75rem;
  padding: 1.5rem;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  background: var(--do-text);
  color: var(--do-border-light);
  transition: all 0.3s ease;
  resize: vertical;
  min-height: 600px;
}

:deep(.json-editor:focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--vt-c-gray-200);
  outline: none;
}

:deep(.json-editor.editor-readonly) {
  background: rgba(255, 255, 255, 0.03);
  color: var(--do-text-muted);
  cursor: not-allowed;
}

:deep(.json-editor.editor-error) {
  border-color: var(--color-danger);
  box-shadow: 0 0 0 3px var(--vt-c-danger-lighter);
}

/* Error Message */
.error-message {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--vt-c-danger-lighter);
  border: 1px solid var(--vt-c-danger-light);
  border-radius: 0.75rem;
  color: var(--color-danger-dark);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}

.error-message i {
  font-size: 1.125rem;
}

/* Save Section */
.save-section {
  display: flex;
  justify-content: center;
  padding-top: 1rem;
  border-top: 1px solid var(--do-border-light);
}

:deep(.save-button) {
  background: var(--gradient-success);
  border: none;
  border-radius: 0.75rem;
  padding: 1rem 2rem;
  font-weight: 600;
  font-size: 1rem;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-success);
}

:deep(.save-button:hover:not(:disabled)) {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px var(--shadow-medium);
}

:deep(.save-button:disabled) {
  background: var(--vt-c-gray-400);
  box-shadow: none;
  cursor: not-allowed;
}

/* Responsive Design */
@media (max-width: 768px) {
  .functions-container {
    padding: 1rem;
  }

  .functions-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
    padding: 1.5rem;
  }

  .header-content {
    flex-direction: column;
    gap: 1rem;
  }

  .header-actions {
    flex-direction: column;
    width: 100%;
    justify-content: stretch;
  }

  :deep(.workflow-selector) {
    min-width: 100%;
  }

  .page-title {
    font-size: 1.4rem;
  }

  .page-subtitle {
    font-size: 1rem;
  }

  .functions-grid {
    grid-template-columns: 1fr;
  }

  .editor-toolbar {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
    padding: 1rem 1.5rem;
  }

  .toolbar-section {
    flex-direction: column;
    gap: 1rem;
  }

  .toolbar-actions {
    justify-content: center;
  }

  .editor-section {
    padding: 1.5rem;
  }

  .editor-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  :deep(.json-editor) {
    font-size: 0.75rem;
    padding: 1rem;
    min-height: 400px;
  }
}

@media (max-width: 480px) {
  .functions-container {
    padding: 0.5rem;
  }

  .icon-wrapper {
    width: 3rem;
    height: 3rem;
    font-size: 1.5rem;
  }

  .page-title {
    font-size: 1.25rem;
  }

  .functions-header {
    padding: 1rem;
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
  :deep(.save-button),
  :deep(.toolbar-button),
  .function-card {
    transition: none;
  }

  .editor-card:hover,
  :deep(.edit-button:hover),
  :deep(.save-button:hover),
  :deep(.toolbar-button:hover),
  .function-card:hover {
    transform: none;
  }

  .editing-dot {
    animation: none;
  }
}
</style>
