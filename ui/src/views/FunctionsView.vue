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
const readonlyViewMode = ref<'visual' | 'json'>('visual')
const showGuideModal = ref(false)
const selectedWorkflowIndex = ref(0)

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

// Get all workflows from JSON
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

// Check if JSON contains a workflow
const hasWorkflow = (): boolean => {
  const workflow = parseJsonToWorkflow()
  return workflow !== null
}

onMounted(async () => {
  await getAssistantProfile()

  if (assistantProfile.value?.functions && assistantProfile.value.functions.trim() !== '') {
    jsonContent.value = assistantProfile.value.functions
    // Auto-detect workflow and set visual mode
    if (hasWorkflow()) {
      currentWorkflow.value = parseJsonToWorkflow()
      readonlyViewMode.value = 'visual'
    }
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
  isEditing.value = !isEditing.value
  if (!isEditing.value) {
    jsonContent.value = JSON.stringify(sampleJson, null, 2)
    jsonError.value = ''
  }
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

  // Ensure selected index is within bounds
  if (selectedWorkflowIndex.value >= workflows.length) {
    selectedWorkflowIndex.value = 0
  }

  return workflows[selectedWorkflowIndex.value]
}

// Toggle between JSON and Visual editor
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

// Handle workflow save from visual editor
const handleWorkflowSave = async (workflow: WorkflowFunction) => {
  jsonContent.value = JSON.stringify([workflow], null, 2)

  // Save to backend
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

// Toggle between visual and JSON in readonly mode
const toggleReadonlyView = () => {
  if (readonlyViewMode.value === 'visual') {
    readonlyViewMode.value = 'json'
  } else {
    currentWorkflow.value = parseJsonToWorkflow()
    if (currentWorkflow.value) {
      readonlyViewMode.value = 'visual'
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

// Handle workflow selection change
const handleWorkflowChange = () => {
  currentWorkflow.value = parseJsonToWorkflow()
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
          <!-- Guide Button -->
          <Button
            label="Guía Rápida"
            icon="pi pi-book"
            class="guide-button"
            severity="help"
            @click="showGuideModal = true"
          />

          <!-- Workflow Selector (only if multiple workflows exist) -->
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

          <!-- Toggle view in readonly mode (only if workflow exists) -->
          <Button
            v-if="!isEditing && hasWorkflow()"
            :label="readonlyViewMode === 'visual' ? 'Ver JSON' : 'Ver Workflow'"
            :icon="readonlyViewMode === 'visual' ? 'pi pi-code' : 'pi pi-sitemap'"
            class="view-toggle-button"
            severity="secondary"
            @click="toggleReadonlyView"
          />

          <!-- Toggle editor mode (only in editing mode) -->
          <Button
            v-if="isEditing"
            :label="editorMode === 'json' ? 'Editor Visual' : 'Editor JSON'"
            :icon="editorMode === 'json' ? 'pi pi-sitemap' : 'pi pi-code'"
            class="mode-toggle-button"
            severity="info"
            @click="toggleEditorMode"
          />

          <!-- Edit/Cancel buttons -->
          <Button
            v-if="!isEditing && editorMode === 'json'"
            label="Editar"
            icon="pi pi-pencil"
            class="edit-button"
            @click="toggleEdit"
          />
          <Button
            v-else-if="editorMode === 'json'"
            label="Cancelar"
            icon="pi pi-times"
            severity="secondary"
            class="cancel-button"
            @click="toggleEdit"
          />
        </div>
      </div>
    </div>

    <!-- Visual Workflow Editor (Editing Mode) -->
    <WorkflowEditor
      v-if="isEditing && editorMode === 'visual'"
      :workflow="currentWorkflow!"
      :readonly="false"
      @save="handleWorkflowSave"
      @update="handleWorkflowUpdate"
    />

    <!-- Visual Workflow Viewer (Readonly Mode) -->
    <WorkflowEditor
      v-else-if="!isEditing && readonlyViewMode === 'visual' && currentWorkflow"
      :workflow="currentWorkflow"
      :readonly="true"
    />

    <!-- Main Editor Card (JSON Mode) -->
    <Card v-else-if="isEditing || readonlyViewMode === 'json'" class="editor-card">
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

            <!-- Error Message -->
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
  background: rgba(255,255,255,0.04);
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
  gap: 1rem;
}

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
  background: rgba(255,255,255,0.04);
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
  background: rgba(255,255,255,0.03);
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
  }

  :deep(.workflow-selector) {
    min-width: 100%;
  }

  .page-title {
    font-size: 2rem;
  }

  .page-subtitle {
    font-size: 1rem;
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
    font-size: 1.75rem;
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
  :deep(.toolbar-button) {
    transition: none;
  }

  .editor-card:hover,
  :deep(.edit-button:hover),
  :deep(.save-button:hover),
  :deep(.toolbar-button:hover) {
    transform: none;
  }

  .editing-dot {
    animation: none;
  }
}
</style>
