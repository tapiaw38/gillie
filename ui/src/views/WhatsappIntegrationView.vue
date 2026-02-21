<script setup lang="ts">
import type { IntegrationParams, WhatsappIntegrationConfig } from '@/types/assistant'
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
  {
    flag: isAddIntegrationError,
    summary: 'Error al guardar configuración',
    detail: addIntegrationError,
  },
  {
    flag: isGetAssistantProfileError,
    summary: 'Error al cargar perfil',
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

  validationErrors.accessToken = !config.accessToken ? 'El token de acceso es obligatorio.' : ''
  validationErrors.phoneNumberId = !config.phoneNumberId
    ? 'El ID de número de teléfono es obligatorio.'
    : ''
  validationErrors.businessAccountId = !config.businessAccountId
    ? 'El ID de cuenta de WhatsApp Business es obligatorio.'
    : ''

  if (
    validationErrors.accessToken ||
    validationErrors.phoneNumberId ||
    validationErrors.businessAccountId
  ) {
    toast.add({
      severity: 'warn',
      summary: 'Campos requeridos',
      detail: 'Por favor completa todos los campos obligatorios',
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
    <!-- Header Section -->
    <div class="header-section">
      <div class="integration-header">
        <div class="icon-wrapper whatsapp-icon">
          <i class="pi pi-whatsapp"></i>
        </div>
        <div class="header-content">
          <h1 class="integration-title">Integración WhatsApp</h1>
          <p class="integration-subtitle">Conecta tu asistente con WhatsApp Business API</p>
        </div>
      </div>

      <div class="activation-toggle">
        <div class="toggle-content">
          <div class="toggle-info">
            <span class="toggle-label">Estado de la integración</span>
            <span class="toggle-status" :class="{ active: whatsappIntegration.activated }">
              {{ whatsappIntegration.activated ? 'Activa' : 'Inactiva' }}
            </span>
          </div>
          <InputSwitch v-model="whatsappIntegration.activated" class="modern-switch" />
        </div>
      </div>
    </div>

    <!-- Configuration Card -->
    <Card class="config-card" :class="{ 'card-disabled': !whatsappIntegration.activated }">
      <template #content>
        <form class="config-form" @submit.prevent="saveConfig">
          <div class="form-grid">
            <div class="field-group">
              <label for="accessToken" class="field-label">
                <i class="pi pi-key field-icon"></i>
                Token de Acceso
              </label>
              <div class="input-wrapper">
                <InputText
                  id="accessToken"
                  v-model="(whatsappIntegration.config as WhatsappIntegrationConfig).accessToken"
                  placeholder="EAAGZ..."
                  :disabled="!whatsappIntegration.activated"
                  :invalid="!!validationErrors.accessToken"
                  required
                />
              </div>
              <Message v-if="validationErrors.accessToken" severity="error" class="field-error">
                {{ validationErrors.accessToken }}
              </Message>
              <small class="field-help">Token temporal o permanente de la API de WhatsApp</small>
            </div>

            <div class="field-group">
              <label for="phoneNumberId" class="field-label">
                <i class="pi pi-phone field-icon"></i>
                ID de Número de Teléfono
              </label>
              <div class="input-wrapper">
                <InputText
                  id="phoneNumberId"
                  v-model="(whatsappIntegration.config as WhatsappIntegrationConfig).phoneNumberId"
                  placeholder="123456789012345"
                  :disabled="!whatsappIntegration.activated"
                  :invalid="!!validationErrors.phoneNumberId"
                  required
                />
              </div>
              <Message v-if="validationErrors.phoneNumberId" severity="error" class="field-error">
                {{ validationErrors.phoneNumberId }}
              </Message>
              <small class="field-help">Número vinculado a la API de WhatsApp</small>
            </div>

            <div class="field-group">
              <label for="businessAccountId" class="field-label">
                <i class="pi pi-building field-icon"></i>
                ID de Cuenta Business
              </label>
              <div class="input-wrapper">
                <InputText
                  id="businessAccountId"
                  v-model="
                    (whatsappIntegration.config as WhatsappIntegrationConfig).businessAccountId
                  "
                  placeholder="987654321098765"
                  :disabled="!whatsappIntegration.activated"
                  :invalid="!!validationErrors.businessAccountId"
                  required
                />
              </div>
              <Message
                v-if="validationErrors.businessAccountId"
                severity="error"
                class="field-error"
              >
                {{ validationErrors.businessAccountId }}
              </Message>
              <small class="field-help">ID de tu cuenta de WhatsApp Business</small>
            </div>
          </div>

          <div class="form-actions">
            <Button
              type="submit"
              label="Guardar Configuración"
              icon="pi pi-save"
              severity="primary"
              :disabled="!whatsappIntegration.activated"
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
          <span class="status-title">Configuración Actual</span>
        </div>
      </template>
      <template #content>
        <div class="status-grid">
          <div class="status-item">
            <div class="status-label">
              <i class="pi pi-key"></i>
              Token de Acceso
            </div>
            <div class="status-value">
              {{
                searchWhatsappIntegration
                  ? (searchWhatsappIntegration.config as unknown as WhatsappIntegrationConfig)
                      .accessToken || 'No configurado'
                  : 'No configurado'
              }}
            </div>
          </div>

          <div class="status-item">
            <div class="status-label">
              <i class="pi pi-phone"></i>
              ID de Número
            </div>
            <div class="status-value">
              {{
                searchWhatsappIntegration
                  ? (searchWhatsappIntegration.config as unknown as WhatsappIntegrationConfig)
                      .phoneNumberId || 'No configurado'
                  : 'No configurado'
              }}
            </div>
          </div>

          <div class="status-item">
            <div class="status-label">
              <i class="pi pi-building"></i>
              ID de Cuenta Business
            </div>
            <div class="status-value">
              {{
                searchWhatsappIntegration
                  ? (searchWhatsappIntegration.config as unknown as WhatsappIntegrationConfig)
                      .businessAccountId || 'No configurado'
                  : 'No configurado'
              }}
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Toast for Notifications -->
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

/* Header Section (más compacto) */
.header-section {
  margin-bottom: 1.25rem;
}

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

.whatsapp-icon {
  background: linear-gradient(135deg, #25d366 0%, #128c7e 100%);
}

.header-content {
  flex: 1;
}

.integration-title {
  font-size: 1.6rem;
  font-weight: 700;
  color: #1e293b;
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
  font-weight: 400;
}

/* Activation Toggle */
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

.toggle-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.toggle-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: #374151;
}

.toggle-status {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-danger);
  transition: color 0.3s ease;
}

.toggle-status.active {
  color: var(--color-success);
}

:deep(.modern-switch) {
  transform: scale(1.1);
}

/* Configuration Card (compacto) */
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

:deep(.config-card .p-card-content) {
  padding: 1rem;
}

.config-form {
  width: 100%;
}

.form-grid {
  display: grid;
  gap: 1rem;
  margin-bottom: 1rem;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #374151;
}

.field-icon {
  color: var(--color-primary);
  font-size: 1rem;
}

.input-wrapper {
  position: relative;
}

/* Input Styles - using PrimeVue classes */

.field-error {
  margin-top: 0.35rem;
}

.field-help {
  color: #64748b;
  font-size: 0.85rem;
  font-style: italic;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.75rem;
  border-top: 1px solid #e2e8f0;
}

/* Button Styles - using PrimeVue classes */

/* Status Card (compacto) */
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

.status-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-icon {
  color: var(--color-primary);
  font-size: 1.125rem;
}

.status-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: #374151;
}

:deep(.status-card .p-card-content) {
  padding: 1rem;
}

.status-grid {
  display: grid;
  gap: 1rem;
}

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

.status-label i {
  color: var(--color-primary);
}

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

/* Responsive Design */
@media (max-width: 768px) {
  .integration-container {
    padding: 0.75rem;
  }

  .integration-header {
    flex-direction: column;
    text-align: center;
    gap: 0.75rem;
  }

  .integration-title {
    font-size: 1.4rem;
  }

  .integration-subtitle {
    font-size: 0.95rem;
  }

  .toggle-content {
    flex-direction: column;
    gap: 0.75rem;
    text-align: center;
  }

  :deep(.config-card .p-card-content),
  :deep(.status-card .p-card-content) {
    padding: 1rem;
  }

  :deep(.status-card .p-card-header) {
    padding: 0.75rem 1rem;
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
    font-size: 1.25rem;
  }

  .activation-toggle,
  :deep(.config-card .p-card-content),
  :deep(.status-card .p-card-content) {
    padding: 0.75rem;
  }

  :deep(.status-card .p-card-header) {
    padding: 0.75rem;
  }
}

@media (min-width: 992px) {
  .integration-container {
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 1rem;
    align-items: start;
  }

  .config-card {
    grid-column: 1 / 2;
  }

  .status-card {
    grid-column: 2 / 3;
    position: sticky;
    top: 5.2rem;
    align-self: start;
  }
}
</style>
