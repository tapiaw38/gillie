<script setup lang="ts">
import type { IntegrationParams, SystemCommandsIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, ref } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useErrorToast } from '@/composables/useErrorToast'
import Toast from 'primevue/toast'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputSwitch from 'primevue/inputswitch'
import Tag from 'primevue/tag'

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

const integration = reactive<IntegrationParams>({
  name: 'system_commands',
  type: 'integration',
  activated: false,
  config: {
    blacklist: [],
    require_confirmation: true,
  } as unknown as SystemCommandsIntegrationConfig,
})

const newPattern = ref('')

const blacklist = computed<string[]>(() => {
  const cfg = integration.config as unknown as SystemCommandsIntegrationConfig
  return Array.isArray(cfg.blacklist) ? cfg.blacklist : []
})

const HARDCODED_BLACKLIST = [
  'rm -rf /', 'rm -rf /*', 'mkfs', 'dd if=', ':(){ :|:& };:',
  '> /dev/sda', 'shred', 'fdisk', 'parted', 'wipefs',
  'shutdown', 'reboot', 'halt', 'poweroff', 'init 0', 'init 6',
]

const saveIntegration = async () => {
  try {
    await addIntegration(integration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error al guardar integración:', error)
  }
}

const toggleActivated = async () => {
  await saveIntegration()
}

const addPattern = async () => {
  const pattern = newPattern.value.trim()
  if (!pattern) return
  const cfg = integration.config as unknown as SystemCommandsIntegrationConfig
  if (!cfg.blacklist.includes(pattern)) {
    cfg.blacklist = [...cfg.blacklist, pattern]
    await saveIntegration()
    toast.add({ severity: 'success', summary: 'Patrón agregado', life: 2000 })
  }
  newPattern.value = ''
}

const removePattern = async (pattern: string) => {
  const cfg = integration.config as unknown as SystemCommandsIntegrationConfig
  cfg.blacklist = cfg.blacklist.filter((p) => p !== pattern)
  await saveIntegration()
  toast.add({ severity: 'info', summary: 'Patrón eliminado', life: 2000 })
}

onMounted(async () => {
  await getAssistantProfile()
  assistantProfile.value?.integrations?.forEach((i) => {
    if (i.name === 'system_commands') {
      integration.activated = i.activated || false
      const cfg = integration.config as unknown as SystemCommandsIntegrationConfig
      const saved = i.config as unknown as SystemCommandsIntegrationConfig
      cfg.blacklist = Array.isArray(saved?.blacklist) ? [...saved.blacklist] : []
      cfg.require_confirmation = saved?.require_confirmation !== false
    }
  })
})
</script>

<template>
  <div class="integration-container">
    <!-- Header -->
    <div class="header-section">
      <div class="integration-header">
        <div class="icon-wrapper cmd-icon">
          <i class="pi pi-server"></i>
        </div>
        <div class="header-content">
          <h1 class="integration-title">Comandos del Sistema</h1>
          <p class="integration-subtitle">
            Permite al asistente ejecutar comandos en el servidor Linux con confirmación del usuario y lista negra configurable
          </p>
        </div>
      </div>

      <div class="activation-toggle">
        <div class="toggle-content">
          <div class="toggle-info">
            <span class="toggle-label">Estado de la integración</span>
            <span class="toggle-status" :class="{ active: integration.activated }">
              {{ integration.activated ? 'Activa' : 'Inactiva' }}
            </span>
          </div>
          <InputSwitch v-model="integration.activated" class="modern-switch" @change="toggleActivated" />
        </div>
      </div>
    </div>

    <!-- Confirmation Toggle Card -->
    <Card class="config-card" :class="{ 'card-disabled': !integration.activated }">
      <template #header>
        <div class="card-header">
          <i class="pi pi-shield card-header-icon"></i>
          <span>Verificación por código</span>
        </div>
      </template>
      <template #content>
        <div class="confirmation-toggle-row">
          <div class="confirmation-info">
            <span class="confirmation-label">Requerir confirmación antes de ejecutar</span>
            <span class="confirmation-desc">
              <template v-if="(integration.config as unknown as SystemCommandsIntegrationConfig).require_confirmation">
                El asistente propone el comando y el usuario debe responder con un código de 6 caracteres para ejecutarlo.
              </template>
              <template v-else>
                El asistente ejecuta los comandos directamente sin pedir confirmación.
              </template>
            </span>
          </div>
          <InputSwitch
            v-model="(integration.config as unknown as SystemCommandsIntegrationConfig).require_confirmation"
            :disabled="!integration.activated"
            class="modern-switch"
            @change="saveIntegration"
          />
        </div>
      </template>
    </Card>

    <!-- Dynamic Blacklist Card -->
    <Card class="config-card" :class="{ 'card-disabled': !integration.activated }">
      <template #header>
        <div class="card-header">
          <i class="pi pi-list card-header-icon"></i>
          <span>Lista negra personalizada</span>
        </div>
      </template>
      <template #content>
        <p class="section-hint">
          Patrones que el asistente no podrá proponer. Si el comando contiene alguno de estos textos será rechazado.
        </p>

        <div class="add-row">
          <InputText
            v-model="newPattern"
            placeholder="ej: apt remove, pip uninstall, curl | sh"
            :disabled="!integration.activated"
            class="add-input"
            @keyup.enter="addPattern"
          />
          <Button
            icon="pi pi-plus"
            label="Agregar"
            severity="primary"
            :disabled="!integration.activated || !newPattern.trim()"
            @click="addPattern"
          />
        </div>

        <div v-if="blacklist.length" class="pattern-list">
          <div v-for="pattern in blacklist" :key="pattern" class="pattern-item">
            <code class="pattern-text">{{ pattern }}</code>
            <Button
              icon="pi pi-times"
              severity="danger"
              text
              rounded
              size="small"
              :disabled="!integration.activated"
              @click="removePattern(pattern)"
            />
          </div>
        </div>
        <p v-else class="empty-hint">No hay patrones personalizados. Se usará solo la lista negra base.</p>
      </template>
    </Card>

    <!-- Hardcoded Blacklist Card -->
    <Card class="status-card">
      <template #header>
        <div class="card-header">
          <i class="pi pi-lock card-header-icon"></i>
          <span>Lista negra base (siempre bloqueada)</span>
        </div>
      </template>
      <template #content>
        <p class="section-hint">
          Estos comandos están bloqueados de forma permanente y no pueden ser desbloqueados.
        </p>
        <div class="hardcoded-list">
          <Tag
            v-for="entry in HARDCODED_BLACKLIST"
            :key="entry"
            severity="danger"
            class="hardcoded-tag"
          >
            <code>{{ entry }}</code>
          </Tag>
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
  flex-shrink: 0;
}

.cmd-icon { background: linear-gradient(135deg, #0f172a 0%, #334155 100%); }

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

.config-card, .status-card {
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
  margin-bottom: 1.25rem;
}

.card-disabled {
  opacity: 0.6;
  filter: grayscale(0.4);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.9rem 1.25rem;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  border-bottom: 1px solid #e2e8f0;
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
}

.card-header-icon { color: var(--color-primary); font-size: 1.1rem; }

:deep(.config-card .p-card-content),
:deep(.status-card .p-card-content) { padding: 1rem; }

:deep(.config-card .p-card-header),
:deep(.status-card .p-card-header) { padding: 0; }

.section-hint {
  font-size: 0.85rem;
  color: #64748b;
  font-style: italic;
  margin: 0 0 0.75rem;
}

.confirmation-toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.confirmation-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.confirmation-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: #374151;
}

.confirmation-desc {
  font-size: 0.85rem;
  color: #64748b;
  font-style: italic;
}

.add-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.add-input { flex: 1; }

.pattern-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.pattern-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background: #f8fafc;
  border-radius: 0.5rem;
  border: 1px solid #e2e8f0;
}

.pattern-text {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.85rem;
  color: #dc2626;
}

.empty-hint {
  font-size: 0.85rem;
  color: #94a3b8;
  font-style: italic;
  text-align: center;
  padding: 0.75rem 0;
}

.hardcoded-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.hardcoded-tag {
  font-size: 0.8rem;
}

.hardcoded-tag code {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
}

@media (max-width: 768px) {
  .integration-container { padding: 0.75rem; }
  .integration-header { flex-direction: column; text-align: center; gap: 0.75rem; }
  .toggle-content { flex-direction: column; gap: 0.75rem; text-align: center; }
  .add-row { flex-direction: column; }
}

@media (min-width: 992px) {
  .integration-container {
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 1rem;
    align-items: start;
  }
  .header-section { grid-column: 1 / -1; }
  .config-card { grid-column: 1 / 2; }
  .status-card { grid-column: 2 / 3; position: sticky; top: 5.2rem; }
}
</style>
