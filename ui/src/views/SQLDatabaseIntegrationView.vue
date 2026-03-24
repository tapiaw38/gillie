<script setup lang="ts">
import type { IntegrationParams, Integration, SQLDatabaseIntegrationConfig, SQLDatabaseTableEntry } from '@/types/assistant'
import { onMounted, reactive, ref, computed } from 'vue'
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
  removeIntegrationById,
  getAssistantProfile,
  assistantProfile,
  isAddIntegrationError,
  addIntegrationError,
  isRemoveIntegrationByIdError,
  removeIntegrationByIdError,
  isGetAssistantProfileError,
  getAssistantProfileError,
} = useAssistant()

const errorWatchers = [
  { flag: isAddIntegrationError, summary: 'Error al guardar configuración', detail: addIntegrationError },
  { flag: isRemoveIntegrationByIdError, summary: 'Error al eliminar base de datos', detail: removeIntegrationByIdError },
  { flag: isGetAssistantProfileError, summary: 'Error al cargar perfil', detail: getAssistantProfileError },
]

const { toast } = useErrorToast(errorWatchers)

// ── Form state ──────────────────────────────────────────────────────────────
const showAddForm = ref(false)
const editingId = ref<string | null>(null)

const formAlias = ref('')
const formConnectionString = ref('')
const formAllowedTables = reactive<SQLDatabaseTableEntry[]>([{ name: '', description: '' }])
const formDmlPermissions = reactive({ INSERT: false, UPDATE: false, DELETE: false })
const formActivated = ref(false)

const formValidationErrors = reactive({
  alias: '',
  connection_string: '',
  tables: '',
})

// ── Constants ────────────────────────────────────────────────────────────────
const ALWAYS_BLOCKED = ['DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE']

const buildBlockedKeywords = (): string[] =>
  (['INSERT', 'UPDATE', 'DELETE'] as const).filter((op) => !formDmlPermissions[op])

// ── Computed list ────────────────────────────────────────────────────────────
const dbIntegrations = computed<Integration[]>(() =>
  assistantProfile.value?.integrations?.filter(
    (i) => i.type === 'database' || i.name === 'sqldatabase',
  ) ?? [],
)

// ── Table helpers ────────────────────────────────────────────────────────────
const addTable = () => {
  formAllowedTables.push({ name: '', description: '' })
}

const removeTable = (index: number) => {
  if (formAllowedTables.length > 1) {
    formAllowedTables.splice(index, 1)
  }
}

// ── Form open / close ────────────────────────────────────────────────────────
const clearForm = () => {
  formAlias.value = ''
  formConnectionString.value = ''
  formAllowedTables.splice(0, formAllowedTables.length, { name: '', description: '' })
  formDmlPermissions.INSERT = false
  formDmlPermissions.UPDATE = false
  formDmlPermissions.DELETE = false
  formActivated.value = false
  formValidationErrors.alias = ''
  formValidationErrors.connection_string = ''
  formValidationErrors.tables = ''
}

const openAddForm = () => {
  clearForm()
  editingId.value = null
  showAddForm.value = true
}

const openEditForm = (integration: Integration) => {
  clearForm()
  editingId.value = integration.id
  formAlias.value = integration.name
  formActivated.value = integration.activated ?? false

  const saved = integration.config as unknown as Record<string, unknown>
  formConnectionString.value = (saved.connection_string as string) || ''

  if (Array.isArray(saved.allowed_tables) && saved.allowed_tables.length > 0) {
    formAllowedTables.splice(0, formAllowedTables.length, ...(saved.allowed_tables as SQLDatabaseTableEntry[]))
  } else if (saved.allowed_table) {
    formAllowedTables.splice(0, formAllowedTables.length, {
      name: saved.allowed_table as string,
      description: (saved.table_description as string) || '',
    })
  }

  const savedBlocked = saved.blocked_keywords as string[] | undefined
  const blocked = savedBlocked ?? ['INSERT', 'UPDATE', 'DELETE']
  formDmlPermissions.INSERT = !blocked.includes('INSERT')
  formDmlPermissions.UPDATE = !blocked.includes('UPDATE')
  formDmlPermissions.DELETE = !blocked.includes('DELETE')

  showAddForm.value = true
}

const cancelForm = () => {
  showAddForm.value = false
  editingId.value = null
}

// ── Save ─────────────────────────────────────────────────────────────────────
const saveForm = async () => {
  formValidationErrors.alias = !formAlias.value.trim() ? 'El nombre/alias es obligatorio.' : ''
  formValidationErrors.connection_string = !formConnectionString.value.trim()
    ? 'La cadena de conexión es obligatoria.'
    : ''
  const hasValidTable = formAllowedTables.some((t) => t.name.trim())
  formValidationErrors.tables = !hasValidTable ? 'Agregá al menos una tabla con nombre.' : ''

  if (formValidationErrors.alias || formValidationErrors.connection_string || formValidationErrors.tables) {
    toast.add({
      severity: 'warn',
      summary: 'Campos requeridos',
      detail: 'Por favor completa todos los campos obligatorios',
      life: 3000,
    })
    return
  }

  const params: IntegrationParams = {
    ...(editingId.value ? { id: editingId.value } : {}),
    name: formAlias.value.trim(),
    type: 'database',
    activated: formActivated.value,
    config: {
      connection_string: formConnectionString.value,
      allowed_tables: formAllowedTables.filter((t) => t.name.trim()),
      blocked_keywords: buildBlockedKeywords(),
    } as SQLDatabaseIntegrationConfig,
  }

  try {
    await addIntegration(params)
    await getAssistantProfile()
    toast.add({
      severity: 'success',
      summary: editingId.value ? 'Base de datos actualizada' : 'Base de datos guardada',
      life: 3000,
    })
    showAddForm.value = false
    editingId.value = null
  } catch (error) {
    console.error('Error al guardar la base de datos:', error)
  }
}

// ── Delete ───────────────────────────────────────────────────────────────────
const deleteDb = async (id: string) => {
  if (!id) {
    toast.add({ severity: 'warn', summary: 'No se puede eliminar', detail: 'Esta integración no tiene ID', life: 3000 })
    return
  }
  const confirmed = confirm('¿Estás seguro de que querés eliminar esta base de datos?')
  if (!confirmed) return

  try {
    await removeIntegrationById(id)
    await getAssistantProfile()
    toast.add({ severity: 'success', summary: 'Base de datos eliminada', life: 3000 })
  } catch (error) {
    console.error('Error al eliminar la base de datos:', error)
    toast.add({ severity: 'error', summary: 'Error al eliminar', detail: String(error), life: 4000 })
  }
}

// ── Mount ────────────────────────────────────────────────────────────────────
onMounted(async () => {
  await getAssistantProfile()
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
          <h1 class="integration-title">Bases de Datos SQL</h1>
          <p class="integration-subtitle">
            Conecta el asistente a múltiples bases de datos PostgreSQL para consultar datos en tiempo real
          </p>
        </div>
      </div>

      <Button
        label="Agregar base de datos"
        icon="pi pi-plus"
        @click="openAddForm"
      />
    </div>

    <!-- Add / Edit Form -->
    <Card v-if="showAddForm" class="form-card">
      <template #content>
        <h3 class="form-title">{{ editingId ? 'Editar base de datos' : 'Nueva base de datos' }}</h3>

        <form class="config-form" @submit.prevent="saveForm">
          <div class="form-grid">

            <!-- Alias -->
            <div class="field-group">
              <label for="form_alias" class="field-label">
                <i class="pi pi-tag field-icon"></i>
                Nombre / Alias
                <span class="required">*</span>
              </label>
              <div class="input-wrapper">
                <InputText
                  id="form_alias"
                  v-model="formAlias"
                  placeholder="CRM, ERP, Inventario..."
                  :invalid="!!formValidationErrors.alias"
                  class="w-full"
                />
              </div>
              <Message v-if="formValidationErrors.alias" severity="error" class="field-error">
                {{ formValidationErrors.alias }}
              </Message>
              <small class="field-help">Nombre identificador de esta conexión.</small>
            </div>

            <!-- Connection string -->
            <div class="field-group">
              <label for="form_connection_string" class="field-label">
                <i class="pi pi-link field-icon"></i>
                Cadena de conexión
                <span class="required">*</span>
              </label>
              <div class="input-wrapper">
                <InputText
                  id="form_connection_string"
                  v-model="formConnectionString"
                  placeholder="postgresql://user:password@host:5432/database"
                  :invalid="!!formValidationErrors.connection_string"
                  class="w-full"
                />
              </div>
              <Message v-if="formValidationErrors.connection_string" severity="error" class="field-error">
                {{ formValidationErrors.connection_string }}
              </Message>
              <small class="field-help">
                Usá un usuario con permisos <strong>solo de lectura</strong> en las tablas permitidas.
              </small>
            </div>

            <!-- Allowed tables -->
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
                    @click="addTable"
                  />
                </div>

                <div class="tables-list">
                  <div
                    v-for="(table, index) in formAllowedTables"
                    :key="index"
                    class="table-row"
                  >
                    <InputText
                      v-model="table.name"
                      placeholder="nombre_tabla"
                      class="table-name-field"
                    />
                    <InputText
                      v-model="table.description"
                      placeholder="Catálogo de productos con columnas: id, nombre, precio, stock..."
                      class="table-desc-field"
                    />
                    <Button
                      v-if="formAllowedTables.length > 1"
                      type="button"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      size="small"
                      class="table-remove-btn"
                      @click="removeTable(index)"
                    />
                  </div>
                </div>

                <Message v-if="formValidationErrors.tables" severity="error" class="field-error">
                  {{ formValidationErrors.tables }}
                </Message>
                <small class="field-help">
                  El asistente solo podrá consultar estas tablas. Describí las columnas para que sepa qué puede consultar.
                </small>
              </div>
            </div>

            <!-- Permissions -->
            <div class="field-group">
              <div class="permissions-section">
                <div class="permissions-header">
                  <label class="field-label">
                    <i class="pi pi-shield field-icon"></i>
                    Permisos de operaciones
                  </label>
                </div>

                <div class="permissions-list">
                  <div v-for="op in (['INSERT', 'UPDATE', 'DELETE'] as const)" :key="op" class="permission-row">
                    <div class="permission-info">
                      <span class="permission-name">{{ op }}</span>
                      <span class="permission-desc">{{
                        op === 'INSERT' ? 'Insertar nuevas filas' :
                        op === 'UPDATE' ? 'Modificar filas existentes' :
                        'Eliminar filas'
                      }}</span>
                    </div>
                    <InputSwitch v-model="formDmlPermissions[op]" />
                  </div>

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

            <!-- Activated toggle -->
            <div class="field-group">
              <div class="activation-toggle">
                <div class="toggle-content">
                  <div class="toggle-info">
                    <span class="toggle-label">Estado de la integración</span>
                    <span class="toggle-status" :class="{ active: formActivated }">
                      {{ formActivated ? 'Activa' : 'Inactiva' }}
                    </span>
                  </div>
                  <InputSwitch v-model="formActivated" class="modern-switch" />
                </div>
              </div>
            </div>

          </div>

          <div class="form-actions">
            <Button
              type="button"
              label="Cancelar"
              severity="secondary"
              outlined
              @click="cancelForm"
            />
            <Button
              type="submit"
              :label="editingId ? 'Actualizar' : 'Guardar'"
              icon="pi pi-save"
              severity="primary"
            />
          </div>
        </form>
      </template>
    </Card>

    <!-- Empty state -->
    <div v-if="dbIntegrations.length === 0 && !showAddForm" class="empty-state">
      No hay bases de datos configuradas. Agrega una para comenzar.
    </div>

    <!-- Database list -->
    <div
      v-for="db in dbIntegrations"
      :key="db.id"
      class="db-card"
    >
      <div class="db-card-header">
        <span class="db-name">{{ db.name }}</span>
        <span class="db-status" :class="{ active: db.activated }">
          {{ db.activated ? 'Activa' : 'Inactiva' }}
        </span>
      </div>
      <div class="db-card-body">
        <span class="db-conn">{{ (db.config as any).connection_string }}</span>
        <span class="db-tables">{{ (db.config as any).allowed_tables?.length ?? 0 }} tabla(s)</span>
      </div>
      <div class="db-card-actions">
        <Button
          icon="pi pi-pencil"
          outlined
          size="small"
          @click="openEditForm(db)"
        />
        <Button
          icon="pi pi-trash"
          severity="danger"
          text
          size="small"
          @click="deleteDb(db.id)"
        />
      </div>
    </div>

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

.header-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.integration-header {
  display: flex;
  align-items: center;
  gap: 1rem;
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

/* Form card — mirrors config-card */
.form-card {
  margin-bottom: 1.25rem;
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.form-card:hover {
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

:deep(.form-card .p-card-content) { padding: 1rem; }

.form-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 1rem 0;
}

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
  gap: 0.5rem;
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

/* Empty state */
.empty-state {
  text-align: center;
  color: #94a3b8;
  font-size: 0.95rem;
  padding: 2rem;
  background: white;
  border-radius: 0.75rem;
  border: 1px dashed #e2e8f0;
  margin-bottom: 1.25rem;
}

/* Database list cards */
.db-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  padding: 1rem;
  margin-bottom: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  box-shadow: 0 3px 14px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.db-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.db-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.db-name {
  font-weight: 700;
  font-size: 1rem;
  color: #1e293b;
}

.db-status {
  font-size: 0.78rem;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 999px;
  background: #fee2e2;
  color: var(--color-danger, #dc2626);
  transition: background 0.3s ease, color 0.3s ease;
}

.db-status.active {
  background: #dcfce7;
  color: var(--color-success, #15803d);
}

.db-card-body {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0.25rem 0;
  flex-wrap: wrap;
}

.db-conn {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.82rem;
  color: #64748b;
  max-width: 300px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.db-tables {
  font-size: 0.78rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #0369a1;
  white-space: nowrap;
}

.db-card-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

/* Status card (kept for potential reuse) */
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
  .header-section { flex-direction: column; align-items: flex-start; }
  .integration-header { flex-direction: column; text-align: center; gap: 0.75rem; }
  .toggle-content { flex-direction: column; gap: 0.75rem; text-align: center; }
  .form-actions { justify-content: stretch; flex-direction: column-reverse; }
  .table-row { flex-wrap: wrap; }
  .table-name-field { min-width: 100%; flex-shrink: unset; }
  .table-desc-field { width: 100%; }
  .db-conn { max-width: 100%; }
}
</style>
