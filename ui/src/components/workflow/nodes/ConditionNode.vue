<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
import type { WorkflowNodeData } from '@/types/workflow.types'

interface Props {
  data: WorkflowNodeData
  selected?: boolean
}

defineProps<Props>()
</script>

<template>
  <div class="condition-node" :class="{ selected }">
    <Handle type="target" :position="Position.Top" class="node-handle" />

    <div class="node-header">
      <i class="pi pi-question-circle"></i>
      <span>Condition</span>
    </div>

    <div class="node-body">
      <div class="node-title">{{ data.label }}</div>
      <div v-if="data.config?.condition" class="condition-text">
        {{ data.config.condition }}
      </div>
    </div>

    <Handle type="source" :position="Position.Bottom" id="true" class="node-handle success" />
    <Handle
      type="source"
      :position="Position.Right"
      id="false"
      class="node-handle error"
      :style="{ top: '50%' }"
    />
  </div>
</template>

<style scoped>
.condition-node {
  background: white;
  border: 2px solid var(--color-warning);
  border-radius: 1rem;
  min-width: 180px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  position: relative;
}

.condition-node.selected {
  border-color: var(--color-warning-dark);
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2);
}

.node-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--gradient-warning);
  color: white;
  border-radius: 0.875rem 0.875rem 0 0;
}

.node-body {
  padding: 1rem;
}

.node-title {
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.condition-text {
  font-size: 0.75rem;
  color: var(--do-text-muted);
  font-family: monospace;
  background: #f8fafc;
  padding: 0.5rem;
  border-radius: 0.375rem;
}

.node-handle {
  width: 10px;
  height: 10px;
  background: var(--color-primary);
  border: 2px solid white;
}

.node-handle.success {
  background: var(--color-success);
}

.node-handle.error {
  background: var(--color-danger);
}
</style>
