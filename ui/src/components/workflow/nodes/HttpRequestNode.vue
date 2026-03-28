<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
import type { WorkflowNodeData } from '@/types/workflow.types'

interface Props {
  data: WorkflowNodeData
  selected?: boolean
}

const props = defineProps<Props>()

const getMethodColor = (method?: string) => {
  const colors: Record<string, string> = {
    GET: 'var(--color-success)',
    POST: 'var(--color-info)',
    PUT: 'var(--color-warning)',
    DELETE: 'var(--color-danger)'
  }
  return colors[method || 'GET'] || 'var(--vt-c-gray-500)'
}
</script>

<template>
  <div class="http-request-node" :class="{ selected }">
    <Handle type="target" :position="Position.Top" class="node-handle" />

    <div class="node-header" :style="{ backgroundColor: getMethodColor(data.config?.method) }">
      <i class="pi pi-globe"></i>
      <span class="method-badge">{{ data.config?.method || 'GET' }}</span>
    </div>

    <div class="node-body">
      <div class="node-title">{{ data.label }}</div>
      <div v-if="data.config?.url" class="node-url">{{ data.config.url }}</div>
      <div v-if="data.config?.params?.length" class="node-params">
        <i class="pi pi-list"></i>
        <span>{{ data.config.params.length }} params</span>
      </div>
    </div>

    <Handle type="source" :position="Position.Bottom" class="node-handle" />
  </div>
</template>

<style scoped>
.http-request-node {
  background: var(--do-bg);
  border: 2px solid var(--do-border-light);
  border-radius: 0.75rem;
  min-width: 200px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.http-request-node.selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem;
  border-radius: 0.625rem 0.625rem 0 0;
  color: white;
}

.method-badge {
  font-weight: 600;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 0.375rem;
}

.node-body {
  padding: 1rem;
}

.node-title {
  font-weight: 600;
  color: var(--do-text);
  margin-bottom: 0.5rem;
}

.node-url {
  font-size: 0.75rem;
  color: var(--do-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 0.5rem;
}

.node-params {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--color-primary);
}

.node-handle {
  width: 10px;
  height: 10px;
  background: var(--color-primary);
  border: 2px solid white;
}
</style>
