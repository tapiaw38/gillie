<script setup lang="ts">
import type { IntegrationParams, SlackIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, watch } from 'vue'
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

const slackIntegration = reactive<IntegrationParams>({
  name: 'slack',
  type: 'integration',
  activated: false,
  config: {
    bot_token: '',
    signing_secret: '',
  } as SlackIntegrationConfig,
})

const validationErrors = reactive({
  bot_token: '',
})

const saveConfig = async () => {
  const config = slackIntegration.config as SlackIntegrationConfig

  validationErrors.bot_token = !config.bot_token ? 'El Bot Token es obligatorio.' : ''

  if (validationErrors.bot_token) {
    toast.add({
      severity: 'warn',
      summary: 'Campos requeridos',
      detail: 'Por favor completa todos los campos obligatorios',
      life: 3000,
    })
    return
  }

  try {
    await addIntegration(slackIntegration)
    await getAssistantProfile()
    toast.add({ severity: 'success', summary: 'Configuración guardada', life: 3000 })
  } catch (error) {
    console.error('Error al guardar la configuración:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(slackIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error al actualizar integración:', error)
  }
}

watch(() => slackIntegration.activated, async () => {
  await updateIntegration()
})

const currentIntegration = computed(() =>
  assistantProfile.value?.integrations?.find((i) => i.name === 'slack'),
)

const API_BASE = (import.meta.env.VITE_ASSISTANT_BASE_URL as string || 'http://localhost:8000').replace(/\/$/, '')

const webhookUrl = computed(() => `${API_BASE}/api/slack/events`)

onMounted(async () => {
  await getAssistantProfile()
  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'slack') {
      slackIntegration.activated = integration.activated || false
      const config = slackIntegration.config as SlackIntegrationConfig
      const saved = integration.config as unknown as SlackIntegrationConfig
      config.bot_token = saved.bot_token || ''
      config.signing_secret = saved.signing_secret || ''
    }
  })
})
</script>

<template>
  <div class="integration-container">
    <!-- Header -->
    <div class="header-section">
      <div class="integration-header">
        <div class="icon-wrapper slack-icon">
          <i class="pi pi-slack"></i>
        </div>
        <div class="header-content">
          <h1 class="integration-title">Slack</h1>
          <p class="integration-subtitle">
            Conecta el asistente a tu workspace de Slack para responder mensajes automáticamente
          </p>
        </div>
      </div>

      <div class="activation-toggle">
        <div class="toggle-content">
          <div class="toggle-info">
            <span class="toggle-label">Estado de la integración</span>
            <span class="toggle-status" :class="{ active: slackIntegration.activated }">
              {{ slackIntegration.activated ? 'Activa' : 'Inactiva' }}
            </span>
          </div>
          <InputSwitch v-model="slackIntegration.activated" class="modern-switch" />
        </div>
      </div>
    </div>

    <!-- Config Card -->
    <Card class="config-card" :class="{ 'card-disabled': !slackIntegration.activated }">
      <template #content>
        <form class="config-form" @submit.prevent="saveConfig">
          <div class="form-grid">

            <div class="field-group">
              <label for="bot_token" class="field-label">
                <i class="pi pi-key field-icon"></i>
                Bot Token
                <span class="required">*</span>
              </label>
              <div class="input-wrapper">
                <InputText
                  id="bot_token"
                  v-model="(slackIntegration.config as SlackIntegrationConfig).bot_token"
                  placeholder="xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx"
                  :disabled="!slackIntegration.activated"
                  :invalid="!!validationErrors.bot_token"
                  class="w-full"
                  type="password"
                />
              </div>
              <Message v-if="validationErrors.bot_token" severity="error" class="field-error">
                {{ validationErrors.bot_token }}
              </Message>
              <small class="field-help">
                Token OAuth del bot. Lo encontrás en <strong>OAuth &amp; Permissions</strong> de tu Slack App.
              </small>
            </div>

            <div class="field-group">
              <label for="signing_secret" class="field-label">
                <i class="pi pi-lock field-icon"></i>
                Signing Secret
              </label>
              <div class="input-wrapper">
                <InputText
                  id="signing_secret"
                  v-model="(slackIntegration.config as SlackIntegrationConfig).signing_secret"
                  placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  :disabled="!slackIntegration.activated"
                  class="w-full"
                  type="password"
                />
              </div>
              <small class="field-help">
                Recomendado para verificar que los webhooks provienen de Slack. Lo encontrás en <strong>Basic Information</strong>.
              </small>
            </div>

          </div>

          <div class="form-actions">
            <Button
              type="submit"
              label="Guardar Configuración"
              icon="pi pi-save"
              severity="primary"
              :disabled="!slackIntegration.activated"
            />
          </div>
        </form>
      </template>
    </Card>

    <!-- Status / Info Card -->
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
            <div class="status-label"><i class="pi pi-link"></i> Webhook URL</div>
            <div class="status-value webhook-url">{{ webhookUrl }}</div>
            <small class="field-help">Configurá esta URL en <strong>Event Subscriptions</strong> de tu Slack App.</small>
          </div>

          <div class="status-item">
            <div class="status-label"><i class="pi pi-key"></i> Bot Token</div>
            <div class="status-value">
              {{ currentIntegration
                ? (currentIntegration.config as unknown as SlackIntegrationConfig).bot_token
                  ? '•••••••••••••••••••'
                  : 'No configurado'
                : 'No configurado' }}
            </div>
          </div>

          <div class="status-item">
            <div class="status-label"><i class="pi pi-lock"></i> Signing Secret</div>
            <div class="status-value">
              {{ currentIntegration
                ? (currentIntegration.config as unknown as SlackIntegrationConfig).signing_secret
                  ? '•••••••••••••••••••'
                  : 'No configurado'
                : 'No configurado' }}
            </div>
          </div>

        </div>

        <div class="setup-steps">
          <p class="steps-title"><i class="pi pi-info-circle"></i> Pasos de configuración</p>
          <ol class="steps-list">
            <li>Creá una Slack App en <strong>api.slack.com/apps</strong></li>
            <li>En <strong>OAuth &amp; Permissions</strong>, agregá el scope <code>chat:write</code></li>
            <li>Instalá la app en tu workspace y copiá el <strong>Bot Token</strong></li>
            <li>En <strong>Event Subscriptions</strong>, activá y pegá la Webhook URL de arriba</li>
            <li>Suscribite al evento <code>message.channels</code> o <code>message.im</code></li>
            <li>Copiá el <strong>Signing Secret</strong> de Basic Information</li>
          </ol>
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
  background: var(--do-bg);
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

.slack-icon { background: linear-gradient(135deg, #4a154b 0%, #611f69 100%); }

.header-content { flex: 1; }

.integration-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 0.25rem 0;
  color: var(--do-text);
}

.integration-subtitle { font-size: 0.95rem; color: var(--do-text-muted); margin: 0; }

.activation-toggle {
  background: rgba(255,255,255,0.04);
  border-radius: 0.75rem;
  padding: 1rem;
  box-shadow: 0 3px 14px rgba(0, 0, 0, 0.06);
  border: 1px solid var(--vt-c-gray-200);
}

.toggle-content { display: flex; align-items: center; justify-content: space-between; }
.toggle-info { display: flex; flex-direction: column; gap: 0.25rem; }
.toggle-label { font-size: 0.95rem; font-weight: 600; color: var(--do-text); }
.toggle-status { font-size: 0.85rem; font-weight: 500; color: var(--color-danger); transition: color 0.3s; }
.toggle-status.active { color: var(--color-success); }
:deep(.modern-switch) { transform: scale(1.1); }

.config-card {
  margin-bottom: 1.25rem;
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--vt-c-gray-200);
  transition: all 0.2s ease;
}

.config-card:hover { box-shadow: 0 14px 40px rgba(0, 0, 0, 0.12); transform: translateY(-2px); }

.card-disabled { opacity: 0.6; filter: grayscale(0.5); pointer-events: none; }

:deep(.config-card .p-card-content) { padding: 1rem; }

.form-grid { display: grid; gap: 1rem; margin-bottom: 1rem; }
.field-group { display: flex; flex-direction: column; gap: 0.5rem; }

.field-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--do-text);
}

.required { color: var(--color-danger); }
.field-icon { color: var(--color-primary); font-size: 1rem; }
.input-wrapper { position: relative; }
.w-full { width: 100%; }
.field-error { margin-top: 0.35rem; }
.field-help { color: var(--do-text-muted); font-size: 0.85rem; font-style: italic; }

.form-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.75rem;
  border-top: 1px solid var(--vt-c-gray-200);
}

.status-card {
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--vt-c-gray-200);
}

:deep(.status-card .p-card-header) {
  background: rgba(255,255,255,0.04);
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--vt-c-gray-200);
}

.status-header { display: flex; align-items: center; gap: 0.5rem; }
.status-icon { color: var(--color-primary); font-size: 1.125rem; }
.status-title { font-size: 1.05rem; font-weight: 600; color: var(--do-text); }

:deep(.status-card .p-card-content) { padding: 1rem; }

.status-grid { display: grid; gap: 1rem; margin-bottom: 1.25rem; }

.status-item {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.75rem;
  background: rgba(255,255,255,0.04);
  border-radius: 0.6rem;
  border: 1px solid var(--vt-c-gray-200);
}

.status-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--do-text-muted);
}

.status-label i { color: var(--color-primary); }

.status-value {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.85rem;
  color: var(--do-text);
  background: rgba(255,255,255,0.04);
  padding: 0.6rem;
  border-radius: 0.4rem;
  border: 1px solid var(--vt-c-gray-200);
  word-break: break-all;
}

.webhook-url { color: #4a154b; font-weight: 600; }

.setup-steps {
  background: rgba(255,255,255,0.04);
  border-radius: 0.6rem;
  border: 1px solid var(--vt-c-gray-200);
  padding: 0.9rem;
}

.steps-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--do-text);
  margin: 0 0 0.6rem;
}

.steps-title i { color: var(--color-primary); }

.steps-list {
  margin: 0;
  padding-left: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.steps-list li { font-size: 0.85rem; color: var(--do-text-muted); }

.steps-list code {
  background: rgba(255,255,255,0.08);
  padding: 0.1rem 0.35rem;
  border-radius: 0.25rem;
  font-family: 'SF Mono', monospace;
  font-size: 0.8rem;
  color: var(--do-text);
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
    grid-template-columns: 1fr 400px;
    gap: 1rem;
    align-items: start;
  }
  .config-card { grid-column: 1 / 2; }
  .status-card { grid-column: 2 / 3; position: sticky; top: 5.2rem; align-self: start; }
}
</style>
