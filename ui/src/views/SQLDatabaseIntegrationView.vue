<script setup lang="ts">
import type { IntegrationParams, SQLDatabaseIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, watch } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useErrorToast } from '@/composables/useErrorToast'
import Toast from 'primevue/toast'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
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

const sqlIntegration = reactive<IntegrationParams>({
  name: 'sqldatabase',
  type: 'integration',
  activated: false,
  config: {
    connection_string: '',
    allowed_table: '',
    table_description: '',
  } as SQLDatabaseIntegrationConfig,
})

const validationErrors = reactive({
  connection_string: '',
  allowed_table: '',
})

const saveConfig = async () => {
  const config = sqlIntegration.config as SQLDatabaseIntegrationConfig

  validationErrors.connection_string = !config.connection_string
    ? 'La cadena de conexión es obligatoria.'
    : ''
  validationErrors.allowed_table = !config.allowed_table
    ? 'El nombre de la tabla es obligatorio.'
    : ''

  if (validationErrors.connection_string || validationErrors.allowed_table) {
    toast.add({
      severity: 'warn',
      summary: 'Campos requeridos',
      detail: 'Por favor completa todos los campos obligatorios',
      life: 3000,
    })
    return
  }

  try {
    await addIntegration(sqlIntegration)
    await getAssistantProfile()
    toast.add({ severity: 'success', summary: 'Configuración guardada', life: 3000 })
  } catch (error) {
    console.error('Error al guardar la configuración:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(sqlIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error al actualizar integración:', error)
  }
}

watch(() => sqlIntegration.activated, async () => {
  await updateIntegration()
})

const currentIntegration = computed(() =>
  assistantProfile.value?.integrations?.find((i) => i.name === 'sqldatabase'),
)

onMounted(async () => {
  await getAssistantProfile()
  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'sqldatabase') {
      sqlIntegration.activated = integration.activated || false
      const config = sqlIntegration.config as SQLDatabaseIntegrationConfig
      const saved = integration.config as unknown as SQLDatabaseIntegrationConfig
      config.connection_string = saved.connection_string || ''
      config.allowed_table = saved.allowed_table || ''
      config.table_description = saved.table_description || ''
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
            Conecta el asistente a una tabla de PostgreSQL para consultar datos en tiempo real
          </p>
        </div>
      </div>

      <div class="activation-toggle">
        <div class="toggle-content">
          <div class="toggle-info">
            <span class="toggle-label">Estado de la integración</span>
            <span class="toggle-status" :class="{ active: sqlIntegration.activated }">
              {{ sqlIntegration.activated ? 'Activa' : 'Inactiva' }}
            </span>
          </div>
          <InputSwitch v-model="sqlIntegration.activated" class="modern-switch" />
        </div>
      </div>
    </div>

    <!-- Config Card -->
    <Card class="config-card" :class="{ 'card-disabled': !sqlIntegration.activated }">
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
                  v-model="(sqlIntegration.config as SQLDatabaseIntegrationConfig).connection_string"
                  placeholder="postgresql://user:password@host:5432/database"
                  :disabled="!sqlIntegration.activated"
                  :invalid="!!validationErrors.connection_string"
                  class="w-full"
                />
              </div>
              <Message v-if="validationErrors.connection_string" severity="error" class="field-error">
                {{ validationErrors.connection_string }}
              </Message>
              <small class="field-help">
                Usá un usuario con permisos <strong>solo de lectura</strong> en la tabla permitida
              </small>
            </div>

            <div class="field-group">
              <label for="allowed_table" class="field-label">
                <i class="pi pi-table field-icon"></i>
                Tabla permitida
                <span class="required">*</span>
              </label>
              <div class="input-wrapper">
                <InputText
                  id="allowed_table"
                  v-model="(sqlIntegration.config as SQLDatabaseIntegrationConfig).allowed_table"
                  placeholder="productos"
                  :disabled="!sqlIntegration.activated"
                  :invalid="!!validationErrors.allowed_table"
                  class="w-full"
                />
              </div>
              <Message v-if="validationErrors.allowed_table" severity="error" class="field-error">
                {{ validationErrors.allowed_table }}
              </Message>
              <small class="field-help">
                El asistente solo podrá consultar esta tabla. Las demás permanecen inaccesibles.
              </small>
            </div>

            <div class="field-group">
              <label for="table_description" class="field-label">
                <i class="pi pi-info-circle field-icon"></i>
                Descripción de la tabla
              </label>
              <div class="input-wrapper">
                <Textarea
                  id="table_description"
                  v-model="(sqlIntegration.config as SQLDatabaseIntegrationConfig).table_description"
                  placeholder="Catálogo de productos con columnas: id, nombre, precio, stock, categoria, descripcion"
                  :disabled="!sqlIntegration.activated"
                  rows="3"
                  class="w-full"
                />
              </div>
              <small class="field-help">
                Describí las columnas disponibles para que el asistente sepa qué puede consultar
              </small>
            </div>

          </div>

          <div class="form-actions">
            <Button
              type="submit"
              label="Guardar Configuración"
              icon="pi pi-save"
              severity="primary"
              :disabled="!sqlIntegration.activated"
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
              {{ currentIntegration
                ? (currentIntegration.config as unknown as SQLDatabaseIntegrationConfig).connection_string || 'No configurado'
                : 'No configurado' }}
            </div>
          </div>
          <div class="status-item">
            <div class="status-label"><i class="pi pi-table"></i> Tabla permitida</div>
            <div class="status-value">
              {{ currentIntegration
                ? (currentIntegration.config as unknown as SQLDatabaseIntegrationConfig).allowed_table || 'No configurado'
                : 'No configurado' }}
            </div>
          </div>
          <div class="status-item">
            <div class="status-label"><i class="pi pi-info-circle"></i> Descripción</div>
            <div class="status-value description-value">
              {{ currentIntegration
                ? (currentIntegration.config as unknown as SQLDatabaseIntegrationConfig).table_description || 'No configurado'
                : 'No configurado' }}
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

.description-value {
  font-family: inherit;
  white-space: pre-wrap;
}

@media (max-width: 768px) {
  .integration-container { padding: 0.75rem; }
  .integration-header { flex-direction: column; text-align: center; gap: 0.75rem; }
  .toggle-content { flex-direction: column; gap: 0.75rem; text-align: center; }
  .form-actions { justify-content: stretch; }
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
