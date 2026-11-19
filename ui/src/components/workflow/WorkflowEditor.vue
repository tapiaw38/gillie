<script setup lang="ts">
import { ref, watch, markRaw } from 'vue'
import { VueFlow, useVueFlow, Panel } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import type { Node, Edge, Connection, NodeComponent } from '@vue-flow/core'
import Button from 'primevue/button'
import Card from 'primevue/card'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'

import HttpRequestNode from './nodes/HttpRequestNode.vue'
import ConditionNode from './nodes/ConditionNode.vue'
import NodeConfigPanel from './panels/NodeConfigPanel.vue'
import type { HttpMethod, WorkflowFunction, WorkflowNodeData, WorkflowStep } from '@/types/workflow.types'
import { findUnresolvedParams, orderNodesByGraph } from './workflowGraph'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

interface Props {
  workflow?: WorkflowFunction
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
})
const emit = defineEmits<{
  save: [workflow: WorkflowFunction]
  update: [workflow: WorkflowFunction]
}>()

const toast = useToast()
const { t } = useI18n()

const nodeTypes: Record<string, NodeComponent> = {
  httpRequest: markRaw(HttpRequestNode) as NodeComponent,
  condition: markRaw(ConditionNode) as NodeComponent,
}

const { onConnect, addEdges, fitView, removeNodes, removeEdges, updateNode } = useVueFlow()

const nodes = ref<Node<WorkflowNodeData>[]>([])
const edges = ref<Edge[]>([])

const selectedNode = ref<Node<WorkflowNodeData> | null>(null)
const showConfigPanel = ref(false)

let nodeCounter = 1

onConnect((connection: Connection) => {
  addEdges([connection])
  toast.add({
    severity: 'success',
    summary: t('workflow.toast.nodesConnected'),
    detail: t('workflow.toast.nodesConnectedDetail'),
    life: 2000,
  })
})

const handleNodeClick = (event: { node: Node<WorkflowNodeData> }) => {
  if (!props.readonly) {
    selectedNode.value = event.node
    showConfigPanel.value = true
  }
}

const handleNodeUpdate = (nodeId: string, data: Partial<WorkflowNodeData>) => {
  const node = nodes.value.find((n) => n.id === nodeId)
  if (node && node.data) {
    node.data = {
      ...node.data,
      ...data,
      label: data.label !== undefined ? data.label : (node.data.label ?? ''),
      type: data.type !== undefined ? data.type : (node.data.type ?? 'http_request'),
      config: {
        ...((node.data && node.data.config) || {}),
        ...data.config,
      },
    }

    updateNode(nodeId, { data: node.data })

    toast.add({
      severity: 'success',
      summary: t('workflow.toast.nodeUpdated'),
      detail: t('workflow.toast.nodeUpdatedDetail'),
      life: 2000,
    })
  }
}

const handleNodeDelete = (nodeId: string) => {
  const connectedEdges = edges.value.filter((e) => e.source === nodeId || e.target === nodeId)
  if (connectedEdges.length > 0) {
    removeEdges(connectedEdges)
  }

  removeNodes([nodeId])

  showConfigPanel.value = false
  selectedNode.value = null

  toast.add({
    severity: 'info',
    summary: t('workflow.toast.nodeDeleted'),
    detail: t('workflow.toast.nodeDeletedDetail'),
    life: 2000,
  })
}

const handleClosePanel = () => {
  showConfigPanel.value = false
  selectedNode.value = null
}

const addHttpRequestNode = () => {
  const newNode: Node<WorkflowNodeData> = {
    id: `node-${nodeCounter++}`,
    type: 'httpRequest',
    position: {
      x: 250 + Math.random() * 100,
      y: 50 + nodes.value.length * 200,
    },
    data: {
      label: t('workflow.node.newStep'),
      type: 'http_request',
      config: {
        url: '',
        method: 'GET',
        params: [],
        bodyTemplate: '',
        responseMapping: {},
      },
    },
  }

  nodes.value.push(newNode)

  toast.add({
    severity: 'success',
    summary: t('workflow.toast.nodeAdded'),
    detail: t('workflow.toast.nodeAddedHttpDetail'),
    life: 2000,
  })

  selectedNode.value = newNode
  showConfigPanel.value = true
}

const addConditionNode = () => {
  const newNode: Node<WorkflowNodeData> = {
    id: `node-${nodeCounter++}`,
    type: 'condition',
    position: {
      x: 250 + Math.random() * 100,
      y: 50 + nodes.value.length * 200,
    },
    data: {
      label: t('workflow.node.newCondition'),
      type: 'condition',
      config: {
        condition: '',
      },
    },
  }

  nodes.value.push(newNode)

  toast.add({
    severity: 'success',
    summary: t('workflow.toast.nodeAdded'),
    detail: t('workflow.toast.nodeAddedConditionDetail'),
    life: 2000,
  })

  selectedNode.value = newNode
  showConfigPanel.value = true
}

const loadWorkflowFromJson = (workflow: WorkflowFunction) => {
  if (workflow.type !== 'workflow' || !workflow.steps) return

  const newNodes: Node<WorkflowNodeData>[] = []
  const newEdges: Edge[] = []
  let yPosition = 50

  workflow.steps.forEach((step, index) => {
    const nodeId = `step-${index + 1}`

    // Determine node type based on whether it has a URL (HTTP Request) or is purely conditional
    const nodeType = step.url && step.method ? 'httpRequest' : 'condition'

    newNodes.push({
      id: nodeId,
      type: nodeType,
      position: { x: 250, y: yPosition },
      data: {
        label: step.name,
        type: nodeType === 'httpRequest' ? 'http_request' : 'condition',
        config: {
          url: step.url,
          method: step.method,
          params: step.required_params,
          headers: step.headers,
          bodyTemplate: step.body_template,
          responseMapping: step.response_mapping,
          condition: step.condition,
        },
      },
    })

    if (index > 0) {
      newEdges.push({
        id: `e${index}-${index + 1}`,
        source: `step-${index}`,
        target: nodeId,
        label: step.condition || '',
        animated: !!step.condition,
      })
    }

    yPosition += 200
  })

  nodes.value = newNodes
  edges.value = newEdges

  setTimeout(() => fitView({ padding: 0.5 }), 100)
}

const exportToJson = (): WorkflowFunction => {
  const steps: WorkflowStep[] = orderNodesByGraph(nodes.value, edges.value).map((node) => ({
    name: node.data?.label ?? '',
    description: node.data?.label ?? '',
    url: node.data?.config?.url || '',
    method: (node.data?.config?.method as HttpMethod) || 'GET',
    required_params: node.data?.config?.params || [],
    headers: node.data?.config?.headers,
    body_template: node.data?.config?.bodyTemplate,
    response_mapping: node.data?.config?.responseMapping,
    condition: node.data?.config?.condition,
  }))

  return {
    type: 'workflow',
    name: props.workflow?.name || 'custom_workflow',
    description: props.workflow?.description || 'Workflow created with visual editor',
    input_params: props.workflow?.input_params || [],
    examples: props.workflow?.examples || [],
    keywords: props.workflow?.keywords || [],
    steps,
  }
}

const handleSave = () => {
  const workflow = exportToJson()
  const unresolved = findUnresolvedParams(workflow.steps ?? [], props.workflow?.input_params ?? [])
  if (unresolved.length) {
    toast.add({
      severity: 'warn',
      summary: t('workflow.toast.unresolvedParams'),
      detail: t('workflow.toast.unresolvedParamsDetail', { params: unresolved.join(', ') }),
      life: 6000,
    })
  }
  emit('save', workflow)
}

const handleExport = () => {
  const workflow = exportToJson()
  emit('update', workflow)
}

watch(
  () => props.workflow,
  (newWorkflow) => {
    if (newWorkflow) {
      loadWorkflowFromJson(newWorkflow)
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="workflow-editor-container">
    <Card class="editor-card">
      <template #header>
        <div class="editor-header">
          <div class="header-left">
            <i class="pi pi-sitemap"></i>
            <h3>
              {{ readonly ? t('workflow.editor.viewTitle') : t('workflow.editor.title') }}
            </h3>
          </div>
          <div v-if="!readonly" class="header-actions">
            <Button
              v-tooltip.bottom="t('workflow.editor.addHttp')"
              icon="pi pi-plus"
              size="small"
              severity="success"
              @click="addHttpRequestNode"
            />
            <Button
              v-tooltip.bottom="t('workflow.editor.addCondition')"
              icon="pi pi-question"
              size="small"
              severity="warning"
              @click="addConditionNode"
            />
            <Button
              v-tooltip.bottom="t('workflow.editor.reloadFromJson')"
              icon="pi pi-refresh"
              size="small"
              severity="secondary"
              @click="loadWorkflowFromJson(props.workflow!)"
            />
            <Button
              v-tooltip.bottom="t('workflow.editor.exportToJson')"
              icon="pi pi-download"
              size="small"
              severity="info"
              @click="handleExport"
            />
            <Button
              v-tooltip.bottom="t('workflow.editor.saveWorkflow')"
              icon="pi pi-save"
              size="small"
              @click="handleSave"
            />
          </div>
        </div>
      </template>

      <template #content>
        <div class="vue-flow-wrapper">
          <VueFlow
            :nodes="nodes"
            :edges="edges"
            :node-types="nodeTypes"
            :default-zoom="0.5"
            :min-zoom="0.2"
            :max-zoom="4"
            :nodes-draggable="true"
            :nodes-connectable="!readonly"
            :elements-selectable="!readonly"
            fit-view-on-init
            @node-click="handleNodeClick"
          >
            <!-- Background pattern -->
            <Background pattern-color="#e2e8f0" :gap="16" />

            <!-- Controls (zoom, fit view, etc.) -->
            <Controls />

            <!-- Minimap -->
            <MiniMap />

            <!-- Custom panel for instructions -->
            <Panel position="top-left" class="info-panel">
              <div class="panel-content">
                <i class="pi pi-info-circle"></i>
                <span v-if="readonly">{{ t('workflow.editor.infoPanelReadonly') }}</span>
                <span v-else>{{ t('workflow.editor.infoPanelEdit') }}</span>
              </div>
            </Panel>
          </VueFlow>
        </div>
      </template>
    </Card>

    <!-- Node Configuration Panel -->
    <NodeConfigPanel
      v-if="showConfigPanel"
      :selected-node="selectedNode"
      @update="handleNodeUpdate"
      @delete="handleNodeDelete"
      @close="handleClosePanel"
    />
  </div>
</template>

<style scoped>
.workflow-editor-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.editor-card {
  height: 100%;
  border-radius: 1rem;
  overflow: hidden;
  transition: margin-right 0.3s ease;
}

.editor-card:has(~ .config-panel) {
  margin-right: 400px;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem 2rem;
  background: rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid var(--do-border-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-left i {
  font-size: 1.5rem;
  color: var(--color-primary);
}

.header-left h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--do-text);
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.vue-flow-wrapper {
  height: 600px;
  background: var(--do-bg);
  border-radius: 0.5rem;
}

.info-panel {
  background: rgba(255, 255, 255, 0.06);
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
  border: 1px solid var(--do-border-light);
}

.panel-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--do-text-muted);
}

.panel-content i {
  color: var(--color-info);
}

/* Vue Flow custom styles */
:deep(.vue-flow__edge-path) {
  stroke: var(--color-primary);
  stroke-width: 2;
}

:deep(.vue-flow__edge.selected .vue-flow__edge-path) {
  stroke: var(--color-primary-dark);
}

:deep(.vue-flow__edge-text) {
  fill: #1e293b;
  font-size: 12px;
  font-weight: 500;
}

:deep(.vue-flow__edge-textbg) {
  fill: var(--do-bg);
}
</style>
