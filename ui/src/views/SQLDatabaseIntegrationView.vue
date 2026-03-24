<script setup lang="ts">
import type { IntegrationParams, SQLDatabaseIntegrationConfig, SQLDatabaseTableEntry } from '@/types/assistant'
import { onMounted, reactive, ref, computed, watch } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useErrorToast } from '@/composables/useErrorToast'
import Toast from 'primevue/toast'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Message from 'primevue/message'
import InputSwitch from 'primevue/inputswitch'

const {
  addIntegration,
  getAssistantProfile,
  assistantProfile,
  isAddIntegrationError,
  addIntegrationError,
  isGetAssistantProfileError,
  getAssistantProfileError,
} = useAssistant()

const errorWatchers = [
  { flag: isAddIntegrationError, summary: 'Error al guardar configuración', detail: addIntegrationError },
  { flag: isGetAssistantProfileError, summary: 'Error al cargar perfil', detail: getAssistantProfileError },
]

const { toast } = useErrorToast(errorWatchers)

const connection_string = ref('')
const activated = ref(false)
const allowed_tables = reactive<SQLDatabaseTableEntry[]>([{ name: '', description: '' }])

// DML permissions — true = operation is ALLOWED (not blocked)
const dml_permissions = reactive({ INSERT: false, UPDATE: false, DELETE: false })

const ALWAYS_BLOCKED = ['DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE']

const buildBlockedKeywords = (): string[] =>
  (['INSERT', 'UPDATE', 'DELETE'] as const).filter((op) => !dml_permissions[op])

const validationErrors = reactive({
  connection_string: '',
  tables: '',
})

const addTable = () => {
  allowed_tables.push({ name: '', description: '' })
}

const removeTable = (index: number) => {
  if (allowed_tables.length > 1) {
    allowed_tables.splice(index, 1)
  }
}

const saveConfig = async () => {
  validationErrors.connection_string = !connection_string.value.trim()
    ? 'La cadena de conexión es obligatoria.'
    : ''

  const hasValidTable = allowed_tables.some((t) => t.name.trim())
  validationErrors.tables = !hasValidTable ? 'Agregá al menos una tabla con nombre.' : ''

  if (validationErrors.connection_string || validationErrors.tables) {
    toast.add({
      severity: 'warn',
      summary: 'Campos requeridos',
      detail: 'Por favor completa todos los campos obligatorios',
      life: 3000,
    })
    return
  }

  const params: IntegrationParams = {
    name: 'sqldatabase',
    type: 'integration',
    activated: activated.value,
    config: {
      connection_string: connection_string.value,
      allowed_tables: allowed_tables.filter((t) => t.name.trim()),
      blocked_keywords: buildBlockedKeywords(),
    } as SQLDatabaseIntegrationConfig,
  }

  try {
    await addIntegration(params)
    await getAssistantProfile()
    toast.add({ severity: 'success', summary: 'Configuración guardada', life: 3000 })
  } catch (error) {
    console.error('Error al guardar la configuración:', error)
  }
}

const updateIntegration = async () => {
  const params: IntegrationParams = {
    name: 'sqldatabase',
    type: 'integration',
    activated: activated.value,
    config: {
      connection_string: connection_string.value,
      allowed_tables: allowed_tables.filter((t) => t.name.trim()),
      blocked_keywords: buildBlockedKeywords(),
    } as SQLDatabaseIntegrationConfig,
  }

  try {
    await addIntegration(params)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error al actualizar integración:', error)
  }
}

watch(activated, async () => {
  await updateIntegration()
})

const currentIntegration = computed(() =>
  assistantProfile.value?.integrations?.find((i) => i.name === 'sqldatabase'),
)

const currentConfig = computed(
  () => currentIntegration.value?.config as unknown as SQLDatabaseIntegrationConfig | undefined,
)

onMounted(async () => {
  await getAssistantProfile()
  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'sqldatabase') {
      activated.value = integration.activated || false
      const saved = integration.config as unknown as Record<string, unknown>
      connection_string.value = (saved.connection_string as string) || ''

      if (Array.isArray(saved.allowed_tables) && saved.allowed_tables.length > 0) {
        allowed_tables.splice(0, allowed_tables.length, ...saved.allowed_tables as SQLDatabaseTableEntry[])
      } else if (saved.allowed_table) {
        allowed_tables.splice(0, allowed_tables.length, {
          name: saved.allowed_table as string,
          description: (saved.table_description as string) || '',
        })
      }

      const savedBlocked = saved.blocked_keywords as string[] | undefined
      const blocked = savedBlocked ?? ['INSERT', 'UPDATE', 'DELETE']
      dml_permissions.INSERT = !blocked.includes('INSERT')
      dml_permissions.UPDATE = !blocked.includes('UPDATE')
      dml_permissions.DELETE = !blocked.includes('DELETE')
    }
  })
})
</script>

<template>
  <div class="integration-container">
    <!-- Header -->
    <div class="header-section">
      <div class="integration-header">
        <div class="icon-wrapper db-icon">
          <i class="pi pi-database"></i>
        </div>
        <div class="header-content">
          <h1 class="integration-title">Base de Datos SQL</h1>
          <p class="integration-subtitle">
            Conecta el asistente a tablas de PostgreSQL para consultar datos en tiempo real
          </p>
        </div>
      </div>

      <div class="activation-toggle">
        <div class="toggle-content">
          <div class="toggle-info">
            <span class="toggle-label">Estado de la integración</span>
            <span class="toggle-status" :class="{ active: activated }">
              {{ activated ? 'Activa' : 'Inactiva' }}
            </span>
          </div>
          <InputSwitch v-model="activated" class="modern-switch" />
        </div>
      </div>
    </div>

    <!-- Config Card -->
    <Card class="config-card" :class="{ 'card-disabled': !activated }">
      <template #content>
        <form class="config-form" @submit.prevent="saveConfig">
          <div class="form-grid">

            <div class="field-group">
              <label for="connection_string" class="field-label">
                <i class="pi pi-link field-icon"></i>
                Cadena de conexión
                <span class="required">*</span>
              </label>
              <div class="input-wrapper">
                <InputText
                  id="connection_string"
                  v-model="connection_string"
                  placeholder="postgresql://user:password@host:5432/database"
                  :disabled="!activated"
                  :invalid="!!validationErrors.connection_string"
                  class="w-full"
                />
              </div>
              <Message v-if="validationErrors.connection_string" severity="error" class="field-error">
                {{ validationErrors.connection_string }}
              </Message>
              <small class="field-help">
                Usá un usuario con permisos <strong>solo de lectura</strong> en las tablas permitidas
              </small>
            </div>

            <div class="field-group">
              <div class="tables-section">
                <div class="tables-header">
                  <label class="field-label">
                    <i class="pi pi-table field-icon"></i>
                    Tablas permitidas
                    <span class="required">*</span>
                  </label>
                  <Button
                    type="button"
                    label="Agregar tabla"
                    icon="pi pi-plus"
                    outlined
                    size="small"
                    :disabled="!activated"
                    @click="addTable"
                  />
                </div>

                <div class="tables-list">
                  <div
                    v-for="(table, index) in allowed_tables"
                    :key="index"
                    class="table-row"
                  >
                    <InputText
                      v-model="table.name"
                      placeholder="nombre_tabla"
                      :disabled="!activated"
                      class="table-name-field"
                    />
                    <InputText
                      v-model="table.description"
                      placeholder="Catálogo de productos con columnas: id, nombre, precio, stock..."
                      :disabled="!activated"
                      class="table-desc-field"
                    />
                    <Button
                      v-if="allowed_tables.length > 1"
                      type="button"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      size="small"
                      :disabled="!activated"
                      class="table-remove-btn"
                      @click="removeTable(index)"
                    />
                  </div>
                </div>

                <Message v-if="validationErrors.tables" severity="error" class="field-error">
                  {{ validationErrors.tables }}
                </Message>
                <small class="field-help">
                  El asistente solo podrá consultar estas tablas. Describí las columnas para que sepa qué puede consultar.
                </small>
              </div>
            </div>

            <div class="field-group">
              <div class="permissions-section">
                <div class="permissions-header">
                  <label class="field-label">
                    <i class="pi pi-shield field-icon"></i>
                    Permisos de operaciones
                  </label>
                </div>

                <div class="permissions-list">
                  <!-- Configurable DML -->
                  <div v-for="op in (['INSERT', 'UPDATE', 'DELETE'] as const)" :key="op" class="permission-row">
                    <div class="permission-info">
                      <span class="permission-name">{{ op }}</span>
                      <span class="permission-desc">{{
                        op === 'INSERT' ? 'Insertar nuevas filas' :
                        op === 'UPDATE' ? 'Modificar filas existentes' :
                        'Eliminar filas'
                      }}</span>
                    </div>
                    <InputSwitch v-model="dml_permissions[op]" :disabled="!activated" />
                  </div>

                  <!-- Always blocked DDL — read-only -->
                  <div class="always-blocked-row">
                    <i class="pi pi-lock always-blocked-icon"></i>
                    <span class="always-blocked-label">Siempre bloqueado:</span>
                    <div class="always-blocked-tags">
                      <span v-for="kw in ALWAYS_BLOCKED" :key="kw" class="blocked-tag">{{ kw }}</span>
                    </div>
                  </div>
                </div>

                <small class="field-help">
                  SELECT siempre está permitido. DDL (DROP, ALTER…) no puede habilitarse.
                </small>
              </div>
            </div>

          </div>

          <div class="form-actions">
            <Button
              type="submit"
              label="Guardar Configuración"
              icon="pi pi-save"
              severity="primary"
              :disabled="!activated"
            />
          </div>
        </form>
      </template>
    </Card>

    <!-- Status Card -->
    <Card class="status-card">
      <template #header>
        <div class="status-header">
          <i class="pi pi-cog status-icon"></i>
          <span class="status-title">Configuración Actual</span>
        </div>
      </template>
      <template #content>
        <div class="status-grid">
          <div class="status-item">
            <div class="status-label"><i class="pi pi-link"></i> Conexión</div>
            <div class="status-value">
              {{ currentConfig?.connection_string || 'No configurado' }}
            </div>
          </div>
          <div class="status-item">
            <div class="status-label"><i class="pi pi-table"></i> Tablas configuradas</div>
            <div class="status-value">
              <template v-if="currentConfig?.allowed_tables?.length">
                <div class="tables-tags">
                  <span
                    v-for="table in currentConfig.allowed_tables"
                    :key="table.name"
                    class="table-tag"
                    :title="table.description || undefined"
                  >{{ table.name }}</span>
                </div>
              </template>
              <template v-else>No configurado</template>
            </div>
          </div>
          <div class="status-item">
            <div class="status-label"><i class="pi pi-shield"></i> Operaciones permitidas</div>
            <div class="status-value">
              <div class="tables-tags">
                <span class="table-tag allowed-tag">SELECT</span>
                <template v-for="op in ['INSERT', 'UPDATE', 'DELETE']" :key="op">
                  <span
                    v-if="!(currentConfig?.blocked_keywords ?? ['INSERT','UPDATE','DELETE']).includes(op)"
                    class="table-tag allowed-tag"
                  >{{ op }}</span>
                </template>
              </div>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.integration-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem 1.25rem;
  min-height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  box-sizing: border-box;
}

.header-section { margin-bottom: 1.25rem; }

.integration-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
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
}

.db-icon { background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); }

.header-content { flex: 1; }

.integration-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 0.25rem 0;
  background: linear-gradient(135deg, #1e293b 0%, #475569 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.integration-subtitle {
  font-size: 0.95rem;
  color: #64748b;
  margin: 0;
}

.activation-toggle {
  background: white;
  border-radius: 0.75rem;
  padding: 1rem;
  box-shadow: 0 3px 14px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.toggle-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.toggle-info { display: flex; flex-direction: column; gap: 0.25rem; }

.toggle-label { font-size: 0.95rem; font-weight: 600; color: #374151; }

.toggle-status {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-danger);
  transition: color 0.3s ease;
}

.toggle-status.active { color: var(--color-success); }

:deep(.modern-switch) { transform: scale(1.1); }

.config-card {
  margin-bottom: 1.25rem;
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.config-card:hover {
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.card-disabled {
  opacity: 0.6;
  filter: grayscale(0.5);
  pointer-events: none;
}

:deep(.config-card .p-card-content) { padding: 1rem; }

.form-grid { display: grid; gap: 1rem; margin-bottom: 1rem; }

.field-group { display: flex; flex-direction: column; gap: 0.5rem; }

.field-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #374151;
}

.required { color: var(--color-danger); }

.field-icon { color: var(--color-primary); font-size: 1rem; }

.input-wrapper { position: relative; }

.w-full { width: 100%; }

.field-error { margin-top: 0.35rem; }

.field-help { color: #64748b; font-size: 0.85rem; font-style: italic; }

.form-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.75rem;
  border-top: 1px solid #e2e8f0;
}

/* Permissions section */
.permissions-section { display: flex; flex-direction: column; gap: 0.5rem; }

.permissions-header { display: flex; align-items: center; justify-content: space-between; }

.permissions-list { display: flex; flex-direction: column; gap: 0.4rem; }

.permission-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
}

.permission-info { display: flex; flex-direction: column; gap: 0.1rem; }

.permission-name { font-family: 'SF Mono', 'Consolas', monospace; font-size: 0.85rem; font-weight: 600; color: #1e293b; }

.permission-desc { font-size: 0.8rem; color: #64748b; }

.always-blocked-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem;
  padding: 0.5rem 0.75rem;
  background: #fef9f0;
  border: 1px dashed #d1d5db;
  border-radius: 0.5rem;
}

.always-blocked-icon { color: #9ca3af; font-size: 0.85rem; }

.always-blocked-label { font-size: 0.8rem; color: #9ca3af; font-weight: 600; white-space: nowrap; }

.always-blocked-tags { display: flex; flex-wrap: wrap; gap: 0.3rem; }

.blocked-tag {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 0.75rem;
  color: #9ca3af;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  padding: 1px 6px;
  border-radius: 4px;
}

.allowed-tag { background: #dcfce7; color: #15803d; }

/* Tables section */
.tables-section { display: flex; flex-direction: column; gap: 0.5rem; }

.tables-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tables-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.table-row {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.table-name-field {
  min-width: 160px;
  flex-shrink: 0;
}

.table-desc-field { flex: 1; }

.table-remove-btn {
  flex-shrink: 0;
  margin-top: 4px;
}

/* Status card */
.status-card {
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
}

:deep(.status-card .p-card-header) {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e2e8f0;
}

.status-header { display: flex; align-items: center; gap: 0.5rem; }

.status-icon { color: var(--color-primary); font-size: 1.125rem; }

.status-title { font-size: 1.05rem; font-weight: 600; color: #374151; }

:deep(.status-card .p-card-content) { padding: 1rem; }

.status-grid { display: grid; gap: 1rem; }

.status-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #f8fafc;
  border-radius: 0.6rem;
  border: 1px solid #e2e8f0;
}

.status-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: #64748b;
}

.status-label i { color: var(--color-primary); }

.status-value {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.85rem;
  color: #374151;
  background: white;
  padding: 0.6rem;
  border-radius: 0.4rem;
  border: 1px solid #e2e8f0;
  word-break: break-all;
  overflow-wrap: break-word;
}

.tables-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.table-tag {
  background: #e0f2fe;
  color: #0369a1;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
}

@media (max-width: 768px) {
  .integration-container { padding: 0.75rem; }
  .integration-header { flex-direction: column; text-align: center; gap: 0.75rem; }
  .toggle-content { flex-direction: column; gap: 0.75rem; text-align: center; }
  .form-actions { justify-content: stretch; }
  .table-row { flex-wrap: wrap; }
  .table-name-field { min-width: 100%; flex-shrink: unset; }
  .table-desc-field { width: 100%; }
}

@media (min-width: 992px) {
  .integration-container {
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 1rem;
    align-items: start;
  }
  .config-card { grid-column: 1 / 2; }
  .status-card { grid-column: 2 / 3; position: sticky; top: 5.2rem; align-self: start; }
}
</style>
