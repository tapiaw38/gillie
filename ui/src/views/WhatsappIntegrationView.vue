<script setup lang="ts">
import type { IntegrationParams, WhatsappIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, watch } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useErrorToast } from '@/composables/useErrorToast'
import { useI18n } from 'vue-i18n'
import Toast from 'primevue/toast'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
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

const { t } = useI18n()

const errorWatchers = [
  {
    flag: isAddIntegrationError,
    summary: t('systemCommands.errorSaveConfig'),
    detail: addIntegrationError,
  },
  {
    flag: isGetAssistantProfileError,
    summary: t('systemCommands.errorLoadProfile'),
    detail: getAssistantProfileError,
  },
]

const { toast } = useErrorToast(errorWatchers)

const whatsappIntegration = reactive<IntegrationParams>({
  name: 'whatsapp',
  type: 'integration',
  activated: false,
  config: {
    accessToken: '',
    phoneNumberId: '',
    businessAccountId: '',
  } as WhatsappIntegrationConfig,
})

const validationErrors = reactive({
  accessToken: '',
  phoneNumberId: '',
  businessAccountId: '',
})

const saveConfig = async () => {
  const config = whatsappIntegration.config as WhatsappIntegrationConfig

  validationErrors.accessToken = !config.accessToken
    ? t('integrations.whatsapp.accessTokenRequired')
    : ''
  validationErrors.phoneNumberId = !config.phoneNumberId
    ? t('integrations.whatsapp.phoneNumberIdRequired')
    : ''
  validationErrors.businessAccountId = !config.businessAccountId
    ? t('integrations.whatsapp.businessAccountIdRequired')
    : ''

  if (
    validationErrors.accessToken ||
    validationErrors.phoneNumberId ||
    validationErrors.businessAccountId
  ) {
    toast.add({
      severity: 'warn',
      summary: t('common.requiredFields'),
      detail: t('common.completeRequired'),
      life: 3000,
    })
    return
  }

  try {
    await addIntegration(whatsappIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error al guardar la configuración:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(whatsappIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error al actualizar integración:', error)
  }
}

watch(
  () => whatsappIntegration.activated,
  async () => {
    await updateIntegration()
  },
)

const searchWhatsappIntegration = computed(() => {
  return assistantProfile.value?.integrations?.find(
    (integration) => integration.name === 'whatsapp',
  )
})

onMounted(async () => {
  await getAssistantProfile()
  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'whatsapp') {
      whatsappIntegration.activated = integration.activated || false
      const config = whatsappIntegration.config as WhatsappIntegrationConfig
      const integrationConfig = integration.config as unknown as WhatsappIntegrationConfig

      config.accessToken = integrationConfig.accessToken || ''
      config.phoneNumberId = integrationConfig.phoneNumberId || ''
      config.businessAccountId = integrationConfig.businessAccountId || ''
    }
  })
})
</script>

<template>
  <div class="integration-container">
    <!-- Page header row -->
    <div class="page-header">
      <div class="header-left">
        <div class="icon-wrapper whatsapp-icon">
          <i class="pi pi-whatsapp"></i>
        </div>
        <div class="header-text">
          <h1 class="page-title">{{ t('integrations.whatsapp.title') }}</h1>
          <p class="page-subtitle">{{ t('integrations.whatsapp.subtitle') }}</p>
        </div>
      </div>
      <div class="header-toggle">
        <span class="toggle-status" :class="{ active: whatsappIntegration.activated }">
          {{
            whatsappIntegration.activated ? t('integrations.active') : t('integrations.inactive')
          }}
        </span>
        <InputSwitch v-model="whatsappIntegration.activated" />
      </div>
    </div>

    <!-- Panel 1 — API Credentials -->
    <div class="panel" :class="{ 'panel-disabled': !whatsappIntegration.activated }">
      <div class="panel-header">
        <span class="step-badge">1</span>
        <div>
          <p class="panel-title">{{ t('integrations.whatsapp.credentialsTitle') }}</p>
          <p class="panel-subtitle">{{ t('integrations.whatsapp.credentialsSubtitle') }}</p>
        </div>
      </div>

      <form class="panel-body" @submit.prevent="saveConfig">
        <div class="field-group">
          <label for="accessToken" class="field-label">
            <i class="pi pi-key field-icon"></i>
            {{ t('integrations.whatsapp.accessToken') }}
          </label>
          <InputText
            id="accessToken"
            v-model="(whatsappIntegration.config as WhatsappIntegrationConfig).accessToken"
            placeholder="EAAGZ..."
            :disabled="!whatsappIntegration.activated"
            :invalid="!!validationErrors.accessToken"
            type="password"
            class="w-full"
          />
          <Message v-if="validationErrors.accessToken" severity="error" class="field-error">
            {{ validationErrors.accessToken }}
          </Message>
          <small class="field-help">{{ t('integrations.whatsapp.accessTokenHelp') }}</small>
        </div>

        <div class="field-group">
          <label for="phoneNumberId" class="field-label">
            <i class="pi pi-phone field-icon"></i>
            {{ t('integrations.whatsapp.phoneNumberId') }}
          </label>
          <InputText
            id="phoneNumberId"
            v-model="(whatsappIntegration.config as WhatsappIntegrationConfig).phoneNumberId"
            placeholder="123456789012345"
            :disabled="!whatsappIntegration.activated"
            :invalid="!!validationErrors.phoneNumberId"
            class="w-full"
          />
          <Message v-if="validationErrors.phoneNumberId" severity="error" class="field-error">
            {{ validationErrors.phoneNumberId }}
          </Message>
          <small class="field-help">{{ t('integrations.whatsapp.phoneNumberIdHelp') }}</small>
        </div>

        <div class="field-group">
          <label for="businessAccountId" class="field-label">
            <i class="pi pi-building field-icon"></i>
            ID de Cuenta Business
          </label>
          <InputText
            id="businessAccountId"
            v-model="(whatsappIntegration.config as WhatsappIntegrationConfig).businessAccountId"
            placeholder="987654321098765"
            :disabled="!whatsappIntegration.activated"
            :invalid="!!validationErrors.businessAccountId"
            class="w-full"
          />
          <Message v-if="validationErrors.businessAccountId" severity="error" class="field-error">
            {{ validationErrors.businessAccountId }}
          </Message>
          <small class="field-help">ID de tu cuenta de WhatsApp Business</small>
        </div>

        <div class="panel-footer">
          <div></div>
          <Button
            type="submit"
            label="Guardar Configuración"
            icon="pi pi-save"
            severity="primary"
            :disabled="!whatsappIntegration.activated"
          />
        </div>
      </form>
    </div>

    <!-- Panel 2 — Current status -->
    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">2</span>
        <div>
          <p class="panel-title">Estado Actual</p>
          <p class="panel-subtitle">Valores guardados de la integración</p>
        </div>
      </div>

      <div class="panel-body status-body">
        <div class="status-row">
          <span class="status-label">
            <i class="pi pi-key"></i>
            Token de Acceso
          </span>
          <code class="status-value">
            {{
              (searchWhatsappIntegration?.config as unknown as WhatsappIntegrationConfig)
                ?.accessToken
                ? '&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;'
                : 'No configurado'
            }}
          </code>
        </div>

        <div class="status-row">
          <span class="status-label">
            <i class="pi pi-phone"></i>
            ID de Número
          </span>
          <code class="status-value">
            {{
              (searchWhatsappIntegration?.config as unknown as WhatsappIntegrationConfig)
                ?.phoneNumberId || 'No configurado'
            }}
          </code>
        </div>

        <div class="status-row">
          <span class="status-label">
            <i class="pi pi-building"></i>
            ID de Cuenta Business
          </span>
          <code class="status-value">
            {{
              (searchWhatsappIntegration?.config as unknown as WhatsappIntegrationConfig)
                ?.businessAccountId || 'No configurado'
            }}
          </code>
        </div>
      </div>
    </div>

    <!-- Panel 3 — Setup guide -->
    <div class="panel">
      <div class="panel-header">
        <span class="step-badge">3</span>
        <div>
          <p class="panel-title">Guía de Configuración</p>
          <p class="panel-subtitle">Pasos para conectar WhatsApp Business API</p>
        </div>
      </div>

      <ol class="steps-list">
        <li class="step-item">
          <span class="step-num">1</span>
          <span>Ve a <strong>developers.facebook.com</strong> y crea una app</span>
        </li>
        <li class="step-item">
          <span class="step-num">2</span>
          <span>Agrega el producto <strong>"WhatsApp"</strong> a tu app</span>
        </li>
        <li class="step-item">
          <span class="step-num">3</span>
          <span>Copia el <strong>Access Token</strong> del panel de API</span>
        </li>
        <li class="step-item">
          <span class="step-num">4</span>
          <span
            >Copia el <strong>Phone Number ID</strong> y el
            <strong>Business Account ID</strong></span
          >
        </li>
        <li class="step-item">
          <span class="step-num">5</span>
          <span>Activa la integración y guarda los datos</span>
        </li>
        <li class="step-item">
          <span class="step-num">6</span>
          <span>Configura el webhook con URL: <code>/api/whatsapp/webhook</code></span>
        </li>
      </ol>
    </div>

    <Toast position="top-right" />
  </div>
</template>

<style scoped>
/* ── View-specific styles ────────────────────────────────── */
.whatsapp-icon {
  color: #25d366;
}

.field-icon {
  color: var(--color-primary);
  font-size: 0.875rem;
}

.field-help {
  font-size: 0.8rem;
  color: var(--do-text-muted);
  font-style: italic;
}

.field-error {
  margin-top: 0.25rem;
}

/* ── Status panel ────────────────────────────────────────── */
.status-body {
  gap: 0.5rem;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--do-border-light);
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.025);
  flex-wrap: wrap;
}

.status-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--do-text-muted);
  white-space: nowrap;
}

.status-label i {
  color: var(--color-primary);
  font-size: 0.8rem;
}

.status-value {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.8rem;
  color: var(--do-text);
  background: rgba(255, 255, 255, 0.04);
  padding: 0.2rem 0.5rem;
  border-radius: 0.3rem;
  word-break: break-all;
  max-width: 60%;
  text-align: right;
}

/* ── Steps guide ─────────────────────────────────────────── */
.steps-list {
  list-style: none;
  margin: 0;
  padding: 1rem 1.25rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.step-item {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  font-size: 0.875rem;
  color: var(--do-text-muted);
}

.step-num {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 50%;
  border: 1px solid var(--do-border-light);
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--do-text-muted);
  flex-shrink: 0;
}

.step-item code {
  background: rgba(255, 255, 255, 0.07);
  padding: 0.1rem 0.35rem;
  border-radius: 0.3rem;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.78rem;
  color: var(--do-text);
}

@media (max-width: 600px) {
  .status-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.35rem;
  }

  .status-value {
    max-width: 100%;
    text-align: left;
  }
}
</style>
