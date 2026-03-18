<script setup lang="ts">
import type { IntegrationParams, TelegramIntegrationConfig } from '@/types/assistant'
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

const telegramIntegration = reactive<IntegrationParams>({
  name: 'telegram',
  type: 'integration',
  activated: false,
  config: {
    bot_token: '',
    secret_token: '',
  } as TelegramIntegrationConfig,
})

const validationErrors = reactive({
  bot_token: '',
})

const saveConfig = async () => {
  const config = telegramIntegration.config as TelegramIntegrationConfig

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
    await addIntegration(telegramIntegration)
    await getAssistantProfile()
    toast.add({ severity: 'success', summary: 'Configuración guardada', life: 3000 })
  } catch (error) {
    console.error('Error al guardar la configuración:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(telegramIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error al actualizar integración:', error)
  }
}

watch(() => telegramIntegration.activated, async () => {
  await updateIntegration()
})

const currentIntegration = computed(() =>
  assistantProfile.value?.integrations?.find((i) => i.name === 'telegram'),
)

const webhookUrl = computed(() => {
  const base = window.location.origin.includes('localhost')
    ? 'http://localhost:8000'
    : window.location.origin
  return `${base}/api/telegram/webhook`
})

const setWebhookUrl = computed(() => {
  const base = window.location.origin.includes('localhost')
    ? 'http://localhost:8000'
    : window.location.origin
  return `${base}/api/telegram/set-webhook`
})

onMounted(async () => {
  await getAssistantProfile()
  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'telegram') {
      telegramIntegration.activated = integration.activated || false
      const config = telegramIntegration.config as TelegramIntegrationConfig
      const saved = integration.config as unknown as TelegramIntegrationConfig
      config.bot_token = saved.bot_token || ''
      config.secret_token = saved.secret_token || ''
    }
  })
})
</script>

<template>
  <div class="integration-container">
    <!-- Header -->
    <div class="header-section">
      <div class="integration-header">
        <div class="icon-wrapper tg-icon">
          <i class="pi pi-send"></i>
        </div>
        <div class="header-content">
          <h1 class="integration-title">Telegram</h1>
          <p class="integration-subtitle">
            Conecta el asistente a tu bot de Telegram para responder mensajes automáticamente
          </p>
        </div>
      </div>

      <div class="activation-toggle">
        <div class="toggle-content">
          <div class="toggle-info">
            <span class="toggle-label">Estado de la integración</span>
            <span class="toggle-status" :class="{ active: telegramIntegration.activated }">
              {{ telegramIntegration.activated ? 'Activa' : 'Inactiva' }}
            </span>
          </div>
          <InputSwitch v-model="telegramIntegration.activated" class="modern-switch" />
        </div>
      </div>
    </div>

    <!-- Config Card -->
    <Card class="config-card" :class="{ 'card-disabled': !telegramIntegration.activated }">
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
                  v-model="(telegramIntegration.config as TelegramIntegrationConfig).bot_token"
                  placeholder="123456789:ABCDefghIJKlmnoPQRstUVwxyz"
                  :disabled="!telegramIntegration.activated"
                  :invalid="!!validationErrors.bot_token"
                  class="w-full"
                  type="password"
                />
              </div>
              <Message v-if="validationErrors.bot_token" severity="error" class="field-error">
                {{ validationErrors.bot_token }}
              </Message>
              <small class="field-help">
                Token del bot obtenido desde <strong>@BotFather</strong> en Telegram.
              </small>
            </div>

            <div class="field-group">
              <label for="secret_token" class="field-label">
                <i class="pi pi-lock field-icon"></i>
                Secret Token
              </label>
              <div class="input-wrapper">
                <InputText
                  id="secret_token"
                  v-model="(telegramIntegration.config as TelegramIntegrationConfig).secret_token"
                  placeholder="Mi token secreto personalizado"
                  :disabled="!telegramIntegration.activated"
                  class="w-full"
                />
              </div>
              <small class="field-help">
                Opcional. Si lo configurás, el webhook solo acepta requests de Telegram con este token en el header <code>X-Telegram-Bot-Api-Secret-Token</code>.
              </small>
            </div>

          </div>

          <div class="form-actions">
            <Button
              type="submit"
              label="Guardar Configuración"
              icon="pi pi-save"
              severity="primary"
              :disabled="!telegramIntegration.activated"
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
          </div>

          <div class="status-item">
            <div class="status-label"><i class="pi pi-key"></i> Bot Token</div>
            <div class="status-value">
              {{ currentIntegration
                ? (currentIntegration.config as unknown as TelegramIntegrationConfig).bot_token
                  ? '•••••••••••••••••••'
                  : 'No configurado'
                : 'No configurado' }}
            </div>
          </div>

          <div class="status-item">
            <div class="status-label"><i class="pi pi-lock"></i> Secret Token</div>
            <div class="status-value">
              {{ currentIntegration
                ? (currentIntegration.config as unknown as TelegramIntegrationConfig).secret_token
                  ? '•••••••••••••••••••'
                  : 'No configurado'
                : 'No configurado' }}
            </div>
          </div>

        </div>

        <div class="setup-steps">
          <p class="steps-title"><i class="pi pi-info-circle"></i> Pasos de configuración</p>
          <ol class="steps-list">
            <li>Abrí Telegram y hablá con <strong>@BotFather</strong></li>
            <li>Enviá <code>/newbot</code> y seguí las instrucciones</li>
            <li>Copiá el <strong>Bot Token</strong> que te da BotFather</li>
            <li>Guardá la configuración acá arriba</li>
            <li>Registrá el webhook enviando un POST a <code>{{ setWebhookUrl }}</code> con <code>{"webhook_url": "{{ webhookUrl }}"}</code></li>
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

.tg-icon { background: linear-gradient(135deg, #0088cc 0%, #005f8e 100%); }

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

.integration-subtitle { font-size: 0.95rem; color: #64748b; margin: 0; }

.activation-toggle {
  background: white;
  border-radius: 0.75rem;
  padding: 1rem;
  box-shadow: 0 3px 14px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.toggle-content { display: flex; align-items: center; justify-content: space-between; }
.toggle-info { display: flex; flex-direction: column; gap: 0.25rem; }
.toggle-label { font-size: 0.95rem; font-weight: 600; color: #374151; }
.toggle-status { font-size: 0.85rem; font-weight: 500; color: var(--color-danger); transition: color 0.3s; }
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

.status-grid { display: grid; gap: 1rem; margin-bottom: 1.25rem; }

.status-item {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
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
}

.webhook-url { color: #0088cc; font-weight: 600; }

.setup-steps {
  background: #f8fafc;
  border-radius: 0.6rem;
  border: 1px solid #e2e8f0;
  padding: 0.9rem;
}

.steps-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: #374151;
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

.steps-list li { font-size: 0.85rem; color: #475569; }

.steps-list code {
  background: #e2e8f0;
  padding: 0.1rem 0.35rem;
  border-radius: 0.25rem;
  font-family: 'SF Mono', monospace;
  font-size: 0.8rem;
  color: #1e293b;
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
