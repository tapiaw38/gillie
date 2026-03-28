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

    <!-- Unified header row -->
    <div class="page-header">
      <div class="header-left">
        <div class="icon-wrapper cmd-icon">
          <i class="pi pi-server"></i>
        </div>
        <div class="header-text">
          <h1 class="page-title">Comandos del Sistema</h1>
          <p class="page-subtitle">
            Permite al asistente ejecutar comandos en el servidor Linux con confirmación del usuario y lista negra configurable
          </p>
        </div>
      </div>
      <div class="header-toggle">
        <span class="toggle-status" :class="{ active: integration.activated }">
          {{ integration.activated ? 'Activa' : 'Inactiva' }}
        </span>
        <InputSwitch v-model="integration.activated" @change="toggleActivated" />
      </div>
    </div>

    <!-- Confirmation Toggle Panel -->
    <div class="panel" :class="{ 'panel-disabled': !integration.activated }">
      <div class="panel-header">
        <i class="pi pi-shield panel-icon"></i>
        <div>
          <p class="panel-title">Verificación por código</p>
          <p class="panel-subtitle">Control de ejecución de comandos</p>
        </div>
      </div>
      <div class="panel-body">
        <div class="toggle-row">
          <div class="toggle-row-info">
            <span class="toggle-row-label">Requerir confirmación antes de ejecutar</span>
            <span class="toggle-row-desc">
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
            @change="saveIntegration"
          />
        </div>
      </div>
    </div>

    <!-- Dynamic Blacklist Panel -->
    <div class="panel" :class="{ 'panel-disabled': !integration.activated }">
      <div class="panel-header">
        <i class="pi pi-list panel-icon"></i>
        <div>
          <p class="panel-title">Lista negra personalizada</p>
          <p class="panel-subtitle">Patrones de comandos que el asistente no podrá proponer</p>
        </div>
      </div>
      <div class="panel-body">
        <p class="section-hint">
          Si el comando contiene alguno de estos textos será rechazado automáticamente.
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
      </div>
    </div>

    <!-- Hardcoded Blacklist Panel -->
    <div class="panel">
      <div class="panel-header">
        <i class="pi pi-lock panel-icon"></i>
        <div>
          <p class="panel-title">Lista negra base (siempre bloqueada)</p>
          <p class="panel-subtitle">Comandos bloqueados de forma permanente, no configurables</p>
        </div>
      </div>
      <div class="panel-body">
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
      </div>
    </div>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
/* ── Layout ─────────────────────────────────────────────── */
.integration-container {
  max-width: 860px;
  margin: 0 auto;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background: var(--do-bg);
  box-sizing: border-box;
}

/* ── Page header ─────────────────────────────────────────── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border: 1px solid var(--do-border-light);
  border-radius: 0.75rem;
  background: rgba(255, 255, 255, 0.03);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
}

.icon-wrapper {
  flex-shrink: 0;
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  color: #fff;
}

.cmd-icon {
  background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
}

.header-text {
  min-width: 0;
}

.page-title {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0 0 0.2rem;
  line-height: 1.2;
}

.page-subtitle {
  font-size: 0.875rem;
  color: var(--do-text-muted);
  margin: 0;
}

.header-toggle {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

.toggle-status {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-danger);
  transition: color 0.25s;
  white-space: nowrap;
}

.toggle-status.active {
  color: var(--color-success);
}

/* ── Panel ───────────────────────────────────────────────── */
.panel {
  border: 1px solid var(--do-border-light);
  border-radius: 0.75rem;
  overflow: hidden;
  background: var(--do-bg);
}

.panel-disabled {
  opacity: 0.55;
  filter: grayscale(0.4);
  pointer-events: none;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 0.875rem 1.25rem;
  border-bottom: 1px solid var(--do-border-light);
  background: rgba(255, 255, 255, 0.025);
}

.panel-icon {
  font-size: 1.1rem;
  color: var(--color-primary);
  flex-shrink: 0;
}

.panel-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--do-text);
  margin: 0 0 0.15rem;
}

.panel-subtitle {
  font-size: 0.8rem;
  color: var(--do-text-muted);
  margin: 0;
}

.panel-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* ── Confirmation toggle row ─────────────────────────────── */
.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.toggle-row-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.toggle-row-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--do-text);
}

.toggle-row-desc {
  font-size: 0.85rem;
  color: var(--do-text-muted);
  font-style: italic;
}

/* ── Section hint ────────────────────────────────────────── */
.section-hint {
  font-size: 0.85rem;
  color: var(--do-text-muted);
  font-style: italic;
  margin: 0;
}

/* ── Add pattern row ─────────────────────────────────────── */
.add-row {
  display: flex;
  gap: 0.5rem;
}

.add-input {
  flex: 1;
}

/* ── Pattern list ────────────────────────────────────────── */
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
  background: rgba(255, 255, 255, 0.025);
  border-radius: 0.5rem;
  border: 1px solid var(--do-border-light);
}

.pattern-text {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.85rem;
  color: var(--color-danger);
}

.empty-hint {
  font-size: 0.85rem;
  color: var(--do-text-muted);
  font-style: italic;
  text-align: center;
  padding: 0.75rem 0;
  margin: 0;
}

/* ── Hardcoded list ──────────────────────────────────────── */
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

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 600px) {
  .integration-container {
    padding: 0.75rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.875rem;
  }

  .header-toggle {
    align-self: flex-end;
  }

  .add-row {
    flex-direction: column;
  }

  .toggle-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }
}
</style>
