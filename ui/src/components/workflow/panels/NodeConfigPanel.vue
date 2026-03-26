<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Chips from 'primevue/chips'
import type { Node } from '@vue-flow/core'
import type { WorkflowNodeData } from '@/types/workflow.types'

interface Props {
  selectedNode: Node<WorkflowNodeData> | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  update: [nodeId: string, data: Partial<WorkflowNodeData>]
  delete: [nodeId: string]
  close: []
}>()

// HTTP Methods
const httpMethods = [
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
  { label: 'PUT', value: 'PUT' },
  { label: 'DELETE', value: 'DELETE' }
]

// Local state for editing
const editForm = ref({
  label: '',
  url: '',
  method: 'GET',
  params: [] as string[],
  bodyTemplate: '',
  condition: '',
  responseMapping: {} as Record<string, string>
})

// Response mapping as array for easier editing
const responseMappingArray = ref<Array<{ key: string; value: string }>>([])

// Watch for selected node changes
watch(
  () => props.selectedNode,
  (node) => {
    if (node && node.data) {
      editForm.value = {
        label: node.data.label || '',
        url: node.data.config?.url || '',
        method: node.data.config?.method || 'GET',
        params: node.data.config?.params || [],
        bodyTemplate: node.data.config?.bodyTemplate || '',
        condition: node.data.config?.condition || '',
        responseMapping: node.data.config?.responseMapping || {}
      }

      // Convert response mapping to array
      responseMappingArray.value = Object.entries(editForm.value.responseMapping).map(
        ([key, value]) => ({ key, value })
      )
    }
  },
  { immediate: true }
)

// Convert response mapping array back to object
const getResponseMappingObject = (): Record<string, string> => {
  const obj: Record<string, string> = {}
  responseMappingArray.value.forEach((item) => {
    if (item.key && item.value) {
      obj[item.key] = item.value
    }
  })
  return obj
}

// Add new response mapping entry
const addResponseMapping = () => {
  responseMappingArray.value.push({ key: '', value: '' })
}

// Remove response mapping entry
const removeResponseMapping = (index: number) => {
  responseMappingArray.value.splice(index, 1)
}

// Save changes
const handleSave = () => {
  if (!props.selectedNode) return

  const updatedData: Partial<WorkflowNodeData> = {
    label: editForm.value.label,
    config: {
      url: editForm.value.url,
      method: editForm.value.method,
      params: editForm.value.params,
      bodyTemplate: editForm.value.bodyTemplate,
      condition: editForm.value.condition,
      responseMapping: getResponseMappingObject()
    }
  }

  emit('update', props.selectedNode.id, updatedData)
}

// Delete node
const handleDelete = () => {
  if (!props.selectedNode) return
  emit('delete', props.selectedNode.id)
}

// Close panel
const handleClose = () => {
  emit('close')
}

// Check if there are unsaved changes
const hasChanges = computed(() => {
  if (!props.selectedNode || !props.selectedNode.data) return false

  const node = props.selectedNode
  return (
    editForm.value.label !== (node.data?.label || '') ||
    editForm.value.url !== (node.data?.config?.url || '') ||
    editForm.value.method !== (node.data?.config?.method || 'GET') ||
    JSON.stringify(editForm.value.params) !== JSON.stringify(node.data?.config?.params || []) ||
    editForm.value.bodyTemplate !== (node.data?.config?.bodyTemplate || '') ||
    editForm.value.condition !== (node.data?.config?.condition || '')
  )
})
</script>

<template>
  <div v-if="selectedNode" class="config-panel">
    <Card class="config-card">
      <template #header>
        <div class="panel-header">
          <div class="header-info">
            <i class="pi pi-cog"></i>
            <div>
              <h3>Configuración del Nodo</h3>
              <p>{{ selectedNode.data?.type === 'http_request' ? 'HTTP Request' : 'Condition' }}</p>
            </div>
          </div>
          <Button
            icon="pi pi-times"
            severity="secondary"
            text
            rounded
            @click="handleClose"
          />
        </div>
      </template>

      <template #content>
        <div class="config-form">
          <!-- Node Label -->
          <div class="form-field">
            <label for="node-label">
              <i class="pi pi-tag"></i>
              Nombre del Paso
            </label>
            <InputText
              id="node-label"
              v-model="editForm.label"
              placeholder="Ej: Validar datos del cliente"
            />
          </div>

          <!-- URL -->
          <div class="form-field">
            <label for="node-url">
              <i class="pi pi-link"></i>
              URL del Endpoint
            </label>
            <InputText
              id="node-url"
              v-model="editForm.url"
              placeholder="https://api.example.com/endpoint"
            />
          </div>

          <!-- HTTP Method -->
          <div class="form-field">
            <label for="node-method">
              <i class="pi pi-globe"></i>
              Método HTTP
            </label>
            <Dropdown
              id="node-method"
              v-model="editForm.method"
              :options="httpMethods"
              option-label="label"
              option-value="value"
              placeholder="Selecciona método"
            />
          </div>

          <!-- Parameters -->
          <div class="form-field">
            <label for="node-params">
              <i class="pi pi-list"></i>
              Parámetros Requeridos
            </label>
            <Chips
              id="node-params"
              v-model="editForm.params"
              placeholder="Presiona Enter para agregar"
            />
            <small>Ej: customer_name, email, phone</small>
          </div>

          <!-- Body Template -->
          <div class="form-field">
            <label for="node-body">
              <i class="pi pi-file"></i>
              Body Template (JSON)
            </label>
            <Textarea
              id="node-body"
              v-model="editForm.bodyTemplate"
              :rows="5"
              placeholder='{"name": "{customer_name}", "email": "{email}"}'
            />
          </div>

          <!-- Condition -->
          <div class="form-field">
            <label for="node-condition">
              <i class="pi pi-question-circle"></i>
              Condición (Opcional)
            </label>
            <InputText
              id="node-condition"
              v-model="editForm.condition"
              placeholder="is_valid == true"
            />
            <small>Condición para ejecutar este paso</small>
          </div>

          <!-- Response Mapping -->
          <div class="form-field">
            <div class="field-header">
              <label>
                <i class="pi pi-arrows-h"></i>
                Mapeo de Respuesta
              </label>
              <Button
                icon="pi pi-plus"
                size="small"
                severity="success"
                text
                @click="addResponseMapping"
              />
            </div>

            <div v-for="(item, index) in responseMappingArray" :key="index" class="mapping-row">
              <InputText
                v-model="item.key"
                placeholder="Variable"
                class="mapping-input"
              />
              <i class="pi pi-arrow-right"></i>
              <InputText
                v-model="item.value"
                placeholder="data.field"
                class="mapping-input"
              />
              <Button
                icon="pi pi-trash"
                size="small"
                severity="danger"
                text
                @click="removeResponseMapping(index)"
              />
            </div>

            <small v-if="responseMappingArray.length === 0">
              Agrega mapeos para extraer datos de la respuesta
            </small>
          </div>

          <!-- Actions -->
          <div class="form-actions">
            <Button
              label="Guardar Cambios"
              icon="pi pi-check"
              :disabled="!hasChanges"
              @click="handleSave"
            />
            <Button
              label="Eliminar Nodo"
              icon="pi pi-trash"
              severity="danger"
              outlined
              @click="handleDelete"
            />
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.config-panel {
  position: fixed;
  right: 0;
  top: 0;
  bottom: 0;
  width: 400px;
  background: white;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  overflow-y: auto;
}

.config-card {
  height: 100%;
  border-radius: 0;
  border: none;
}

:deep(.config-card .p-card-header) {
  padding: 1.5rem;
  background: var(--gradient-primary);
  border-bottom: 1px solid #e2e8f0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: white;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-info i {
  font-size: 1.5rem;
}

.header-info h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
}

.header-info p {
  margin: 0;
  font-size: 0.875rem;
  opacity: 0.9;
}

:deep(.config-card .p-card-content) {
  padding: 1.5rem;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #374151;
  font-size: 0.875rem;
}

.form-field label i {
  color: var(--color-primary);
}

.form-field small {
  color: var(--do-text-muted);
  font-size: 0.75rem;
}

.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.mapping-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #f8fafc;
  border-radius: 0.5rem;
}

.mapping-input {
  flex: 1;
}

.mapping-row i.pi-arrow-right {
  color: var(--color-primary);
}

.form-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

:deep(.form-actions .p-button) {
  width: 100%;
}

/* Scrollbar styling */
.config-panel::-webkit-scrollbar {
  width: 8px;
}

.config-panel::-webkit-scrollbar-track {
  background: var(--do-text);
}

.config-panel::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

.config-panel::-webkit-scrollbar-thumb:hover {
  background: var(--do-text-secondary);
}
</style>
