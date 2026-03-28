<script setup lang="ts">
import type { IntegrationParams, MeliIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, watch } from 'vue'
import { useAssistant } from '@/composables/useAssistant'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Message from 'primevue/message'
import InputSwitch from 'primevue/inputswitch'

const { t } = useI18n()
const { addIntegration, getAssistantProfile, assistantProfile } = useAssistant()

const meliIntegration = reactive<IntegrationParams>({
  name: 'meli',
  type: 'integration',
  activated: false,
  config: {
    app_id: '',
    client_secret: '',
  } as MeliIntegrationConfig,
})

const validationErrors = reactive({
  app_id: '',
  client_secret: '',
})

const saveConfig = async () => {
  const config = meliIntegration.config as MeliIntegrationConfig

  validationErrors.app_id = !config.app_id ? t('integrations.mercadolibre.appIdRequired') : ''
  validationErrors.client_secret = !config.client_secret ? t('integrations.mercadolibre.clientSecretRequired') : ''

  if (validationErrors.app_id || validationErrors.client_secret) {
    return
  }
  try {
    await addIntegration(meliIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error at saving configuration:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(meliIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error al actualizar integración:', error)
  }
}

watch(
  () => meliIntegration.activated,
  async () => {
    await updateIntegration()
  },
)

const searchMeliIntegration = computed(() => {
  return assistantProfile.value?.integrations?.find((integration) => integration.name === 'meli')
})

onMounted(async () => {
  await getAssistantProfile()
  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'meli') {
      meliIntegration.activated = integration.activated || false

      const config = meliIntegration.config as MeliIntegrationConfig
      const integrationConfig = integration.config as unknown as MeliIntegrationConfig

      config.app_id = integrationConfig.app_id || ''
      config.client_secret = integrationConfig.client_secret || ''
    }
  })
})
</script>

<template>
  <div class="integration-container">
    <!-- Header Section -->
    <div class="header-section">
      <div class="integration-header">
        <div class="icon-wrapper mercadolibre-icon">
          <i class="pi pi-shopping-cart"></i>
        </div>
        <div class="header-content">
          <h1 class="integration-title">{{ t('integrations.mercadolibre.title') }}</h1>
          <p class="integration-subtitle">{{ t('integrations.mercadolibre.subtitle') }}</p>
        </div>
      </div>

      <div class="activation-toggle">
        <div class="toggle-content">
          <div class="toggle-info">
            <span class="toggle-label">{{ t('integrations.mercadolibre.integrationStatus') }}</span>
            <span class="toggle-status" :class="{ active: meliIntegration.activated }">
              {{ meliIntegration.activated ? t('integrations.active') : t('integrations.inactive') }}
            </span>
          </div>
          <InputSwitch v-model="meliIntegration.activated" class="modern-switch" />
        </div>
      </div>
    </div>

    <!-- Configuration Card -->
    <Card class="config-card" :class="{ 'card-disabled': !meliIntegration.activated }">
      <template #content>
        <form class="config-form" @submit.prevent="saveConfig">
          <div class="form-grid">
            <div class="field-group">
              <label for="app_id" class="field-label">
                <i class="pi pi-id-card field-icon"></i>
                App ID
              </label>
              <div class="input-wrapper">
                <InputText
                  id="app_id"
                  v-model="(meliIntegration.config as MeliIntegrationConfig).app_id"
                  placeholder="123456789"
                  :disabled="!meliIntegration.activated"
                  :invalid="!!validationErrors.app_id"
                  required
                />
              </div>
              <Message v-if="validationErrors.app_id" severity="error" class="field-error">
                {{ validationErrors.app_id }}
              </Message>
              <small class="field-help">{{ t('integrations.mercadolibre.appIdHelp') }}</small>
            </div>

            <div class="field-group">
              <label for="client_secret" class="field-label">
                <i class="pi pi-lock field-icon"></i>
                Client Secret
              </label>
              <div class="input-wrapper">
                <InputText
                  id="client_secret"
                  v-model="(meliIntegration.config as MeliIntegrationConfig).client_secret"
                  placeholder="APP_USR-xxxxxxxxxxxxxxxxxxxxx"
                  :disabled="!meliIntegration.activated"
                  :invalid="!!validationErrors.client_secret"
                  required
                />
              </div>
              <Message v-if="validationErrors.client_secret" severity="error" class="field-error">
                {{ validationErrors.client_secret }}
              </Message>
              <small class="field-help">{{ t('integrations.mercadolibre.clientSecretHelp') }}</small>
            </div>
          </div>

          <div class="form-actions">
            <Button
              type="submit"
              :label="t('integrations.saveConfig')"
              icon="pi pi-save"
              severity="warning"
              :disabled="!meliIntegration.activated"
            />
          </div>
        </form>
      </template>
    </Card>

    <!-- Current Configuration Card -->
    <Card class="status-card">
      <template #header>
        <div class="status-header">
          <i class="pi pi-cog status-icon"></i>
          <span class="status-title">{{ t('integrations.mercadolibre.currentConfig') }}</span>
        </div>
      </template>
      <template #content>
        <div class="status-grid">
          <div class="status-item">
            <div class="status-label">
              <i class="pi pi-id-card"></i>
              App ID
            </div>
            <div class="status-value">
              {{
                searchMeliIntegration
                  ? (searchMeliIntegration.config as unknown as MeliIntegrationConfig).app_id ||
                    t('integrations.notConfigured')
                  : t('integrations.notConfigured')
              }}
            </div>
          </div>

          <div class="status-item">
            <div class="status-label">
              <i class="pi pi-lock"></i>
              Client Secret
            </div>
            <div class="status-value">
              {{
                searchMeliIntegration
                  ? (searchMeliIntegration.config as unknown as MeliIntegrationConfig)
                      .client_secret || t('integrations.notConfigured')
                  : t('integrations.notConfigured')
              }}
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.integration-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
}

/* Header Section */
.header-section {
  margin-bottom: 2rem;
}

.integration-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.icon-wrapper {
  width: 4rem;
  height: 4rem;
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: white;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.mercadolibre-icon {
  background: linear-gradient(135deg, #ffe600 0%, #ffb800 100%);
  color: #333;
}

.header-content {
  flex: 1;
}

.integration-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
  color: var(--do-text);
}

.integration-subtitle {
  font-size: 1.125rem;
  color: var(--do-text-muted);
  margin: 0;
  font-weight: 400;
}

/* Activation Toggle */
.activation-toggle {
  background: white;
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
}

.toggle-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.toggle-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.toggle-label {
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
}

.toggle-status {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-danger);
  transition: color 0.3s ease;
}

.toggle-status.active {
  color: var(--color-success);
}

:deep(.modern-switch) {
  transform: scale(1.2);
}

/* Configuration Card */
.config-card {
  margin-bottom: 2rem;
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.config-card:hover {
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.card-disabled {
  opacity: 0.6;
  filter: grayscale(0.5);
  pointer-events: none;
}

:deep(.config-card .p-card-content) {
  padding: 2rem;
}

.config-form {
  width: 100%;
}

.form-grid {
  display: grid;
  gap: 2rem;
  margin-bottom: 2rem;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.field-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
}

.field-icon {
  color: var(--color-warning);
  font-size: 1.125rem;
}

.input-wrapper {
  position: relative;
}

/* Input Styles - using PrimeVue classes */

.field-error {
  margin-top: 0.5rem;
}

.field-help {
  color: var(--do-text-muted);
  font-size: 0.875rem;
  font-style: italic;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

/* Button Styles - using PrimeVue classes */

/* Status Card */
.status-card {
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
}

:deep(.status-card .p-card-header) {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e2e8f0;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.status-icon {
  color: var(--color-warning);
  font-size: 1.25rem;
}

.status-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #374151;
}

:deep(.status-card .p-card-content) {
  padding: 2rem;
}

.status-grid {
  display: grid;
  gap: 1.5rem;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 0.75rem;
  border: 1px solid #e2e8f0;
}

.status-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--do-text-muted);
}

.status-label i {
  color: var(--color-warning);
}

.status-value {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.875rem;
  color: #374151;
  background: white;
  padding: 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #e2e8f0;
  word-break: break-all;
  overflow-wrap: break-word;
}

/* Responsive Design */
@media (max-width: 768px) {
  .integration-container {
    padding: 1rem;
  }

  .integration-header {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .integration-title {
    font-size: 2rem;
  }

  .integration-subtitle {
    font-size: 1rem;
  }

  .toggle-content {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }

  :deep(.config-card .p-card-content),
  :deep(.status-card .p-card-content) {
    padding: 1.5rem;
  }

  :deep(.status-card .p-card-header) {
    padding: 1rem 1.5rem;
  }

  .form-actions {
    justify-content: stretch;
  }

  :deep(.save-button) {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .integration-container {
    padding: 0.5rem;
  }

  .icon-wrapper {
    width: 3rem;
    height: 3rem;
    font-size: 1.5rem;
  }

  .integration-title {
    font-size: 1.75rem;
  }

  .activation-toggle,
  :deep(.config-card .p-card-content),
  :deep(.status-card .p-card-content) {
    padding: 1rem;
  }

  :deep(.status-card .p-card-header) {
    padding: 1rem;
  }
}
</style>
