<script setup lang="ts">
import { inject, ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Chips from 'primevue/chips'
import type { Node } from '@vue-flow/core'
import type { IAssistantService } from '@/services/assistant/assistantService'
import type { HttpMethod, WorkflowNodeData, WorkflowStepTestResponse } from '@/types/workflow.types'

interface Props {
  selectedNode: Node<WorkflowNodeData> | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  update: [nodeId: string, data: Partial<WorkflowNodeData>]
  delete: [nodeId: string]
  close: []
}>()

const { t } = useI18n()

// Injected directly: a one-shot test call needs no store state around it.
const services = inject<{ assistantService: IAssistantService }>('services')

// HTTP Methods
const httpMethods = [
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
  { label: 'PUT', value: 'PUT' },
  { label: 'PATCH', value: 'PATCH' },
  { label: 'DELETE', value: 'DELETE' }
]

// Local state for editing
const editForm = ref({
  label: '',
  url: '',
  method: 'GET',
  params: [] as string[],
  headers: {} as Record<string, string>,
  bodyTemplate: '',
  condition: '',
  responseMapping: {} as Record<string, string>
})

// Response mapping and headers as arrays for easier editing
const responseMappingArray = ref<Array<{ key: string; value: string }>>([])
const headersArray = ref<Array<{ key: string; value: string }>>([])

// Test-run state
const testing = ref(false)
const testResult = ref<WorkflowStepTestResponse | null>(null)
const testContext = ref('{}')

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
        headers: node.data.config?.headers || {},
        condition: node.data.config?.condition || '',
        responseMapping: node.data.config?.responseMapping || {}
      }

      // Convert response mapping to array
      responseMappingArray.value = Object.entries(editForm.value.responseMapping).map(
        ([key, value]) => ({ key, value })
      )
      headersArray.value = Object.entries(editForm.value.headers).map(([key, value]) => ({
        key,
        value
      }))
      testResult.value = null
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

const getHeadersObject = (): Record<string, string> => {
  const obj: Record<string, string> = {}
  headersArray.value.forEach((item) => {
    if (item.key) obj[item.key] = item.value
  })
  return obj
}

const addHeader = () => {
  headersArray.value.push({ key: '', value: '' })
}

const removeHeader = (index: number) => {
  headersArray.value.splice(index, 1)
}

/**
 * Run this one step against the real endpoint.
 *
 * Response mapping needs the exact shape of the response, and the only way to
 * learn it used to be saving the workflow, sending a real message and reading
 * the server log.
 */
const runTest = async () => {
  testing.value = true
  testResult.value = null
  try {
    let context: Record<string, string> = {}
    try {
      context = JSON.parse(testContext.value || '{}')
    } catch {
      testResult.value = { ok: false, error: t('workflow.config.testContextInvalid'), elapsed_ms: 0 }
      return
    }
    if (!services) throw new Error('Services not provided')
    testResult.value = await services.assistantService.testWorkflowStep({
      step: {
        name: editForm.value.label || 'test_step',
        url: editForm.value.url,
        method: editForm.value.method as HttpMethod,
        headers: getHeadersObject(),
        body_template: editForm.value.bodyTemplate || undefined
      },
      context
    })
  } catch (error) {
    testResult.value = {
      ok: false,
      error: error instanceof Error ? error.message : String(error),
      elapsed_ms: 0
    }
  } finally {
    testing.value = false
  }
}

const useMappingPath = (path: string) => {
  responseMappingArray.value.push({ key: path.split('.').pop() ?? path, value: path })
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
      headers: getHeadersObject(),
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
              <h3>{{ t('workflow.config.title') }}</h3>
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
              {{ t('workflow.config.stepName') }}
            </label>
            <InputText
              id="node-label"
              v-model="editForm.label"
              :placeholder="t('workflow.config.stepNamePlaceholder')"
            />
          </div>

          <!-- URL -->
          <div class="form-field">
            <label for="node-url">
              <i class="pi pi-link"></i>
              {{ t('workflow.config.endpointUrl') }}
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
              {{ t('workflow.config.httpMethod') }}
            </label>
            <Dropdown
              id="node-method"
              v-model="editForm.method"
              :options="httpMethods"
              option-label="label"
              option-value="value"
              :placeholder="t('workflow.config.selectMethod')"
            />
          </div>

          <!-- Parameters -->
          <div class="form-field">
            <label for="node-params">
              <i class="pi pi-list"></i>
              {{ t('workflow.config.requiredParams') }}
            </label>
            <Chips
              id="node-params"
              v-model="editForm.params"
              :placeholder="t('workflow.config.paramsPlaceholder')"
            />
            <small>{{ t('workflow.config.paramsHint') }}</small>
          </div>

          <!-- Headers -->
          <div class="form-field">
            <div class="field-header">
              <label>
                <i class="pi pi-key"></i>
                {{ t('workflow.config.headers') }}
              </label>
              <Button
                icon="pi pi-plus"
                text
                rounded
                size="small"
                @click="addHeader"
                v-tooltip.left="t('workflow.config.addHeader')"
              />
            </div>
            <div v-for="(item, index) in headersArray" :key="`h-${index}`" class="mapping-row">
              <InputText v-model="item.key" placeholder="Authorization" class="mapping-input" />
              <InputText v-model="item.value" placeholder="Bearer {auth_token}" class="mapping-input" />
              <Button
                icon="pi pi-times"
                text
                rounded
                severity="danger"
                size="small"
                @click="removeHeader(index)"
              />
            </div>
            <small>{{ t('workflow.config.headersHint') }}</small>
          </div>

          <!-- Body Template -->
          <div class="form-field">
            <label for="node-body">
              <i class="pi pi-file"></i>
              {{ t('workflow.config.bodyTemplate') }}
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
              {{ t('workflow.config.condition') }}
            </label>
            <InputText
              id="node-condition"
              v-model="editForm.condition"
              placeholder="is_valid == true"
            />
            <small>{{ t('workflow.config.conditionHint') }}</small>
          </div>

          <!-- Test run -->
          <div class="form-field test-field">
            <div class="field-header">
              <label>
                <i class="pi pi-play"></i>
                {{ t('workflow.config.testStep') }}
              </label>
              <Button
                :label="t('workflow.config.runTest')"
                icon="pi pi-bolt"
                size="small"
                :loading="testing"
                :disabled="!editForm.url"
                @click="runTest"
              />
            </div>
            <Textarea
              v-model="testContext"
              :rows="2"
              placeholder='{"customer_name": "Ana", "auth_token": "test-token"}'
            />
            <small>{{ t('workflow.config.testHint') }}</small>

            <div v-if="testResult" class="test-result">
              <div :class="['test-status', testResult.ok ? 'ok' : 'fail']">
                <i :class="testResult.ok ? 'pi pi-check-circle' : 'pi pi-times-circle'"></i>
                {{ testResult.ok ? t('workflow.config.testOk') : t('workflow.config.testFailed') }}
                <span class="test-elapsed">{{ testResult.elapsed_ms }} ms</span>
              </div>
              <pre v-if="testResult.error" class="test-body">{{ testResult.error }}</pre>
              <pre v-else class="test-body">{{ JSON.stringify(testResult.response, null, 2) }}</pre>
              <div v-if="testResult.paths?.length" class="test-paths">
                <small>{{ t('workflow.config.testPathsHint') }}</small>
                <div class="path-chips">
                  <button
                    v-for="path in testResult.paths"
                    :key="path"
                    type="button"
                    class="path-chip"
                    @click="useMappingPath(path)"
                  >
                    {{ path }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Response Mapping -->
          <div class="form-field">
            <div class="field-header">
              <label>
                <i class="pi pi-arrows-h"></i>
                {{ t('workflow.config.responseMapping') }}
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
              {{ t('workflow.config.responseMappingHint') }}
            </small>
          </div>

          <!-- Actions -->
          <div class="form-actions">
            <Button
              :label="t('workflow.config.saveChanges')"
              icon="pi pi-check"
              :disabled="!hasChanges"
              @click="handleSave"
            />
            <Button
              :label="t('workflow.config.deleteNode')"
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
  background: var(--do-bg);
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.4);
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
  border-bottom: 1px solid var(--do-border-light);
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
  color: var(--do-text);
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

.test-field {
  border-top: 1px solid var(--p-content-border-color, rgba(128, 128, 128, 0.25));
  padding-top: 0.75rem;
}

.test-result {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.test-status {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  font-weight: 600;
}

.test-status.ok {
  color: var(--p-green-500, #22c55e);
}

.test-status.fail {
  color: var(--p-red-500, #ef4444);
}

.test-elapsed {
  margin-left: auto;
  font-weight: 400;
  opacity: 0.6;
}

.test-body {
  max-height: 12rem;
  overflow: auto;
  margin: 0;
  padding: 0.5rem;
  font-size: 0.75rem;
  line-height: 1.4;
  border-radius: 0.375rem;
  background: var(--p-content-hover-background, rgba(128, 128, 128, 0.12));
}

.path-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.25rem;
}

.path-chip {
  font-family: inherit;
  font-size: 0.7rem;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  border: 1px solid var(--p-content-border-color, rgba(128, 128, 128, 0.3));
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.path-chip:hover {
  background: var(--p-content-hover-background, rgba(128, 128, 128, 0.15));
}

.mapping-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: rgba(255,255,255,0.05);
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
  border-top: 1px solid var(--do-border-light);
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
