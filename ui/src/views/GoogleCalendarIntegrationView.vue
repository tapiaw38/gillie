<script setup lang="ts">
import type { IntegrationParams, GoogleCalendarIntegrationConfig } from '@/types/assistant'
import { onMounted, reactive, computed, watch, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAssistant } from '@/composables/useAssistant'
import { useCalendar } from '@/composables/useCalendar'
import { useOAuthPopup } from '@/composables/useOAuthPopup'
import { useErrorToast } from '@/composables/useErrorToast'
import Toast from 'primevue/toast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Message from 'primevue/message'
import InputSwitch from 'primevue/inputswitch'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'

const route = useRoute()
const router = useRouter()

const {
  addIntegration,
  getAssistantProfile,
  assistantProfile,
  isAddIntegrationError,
  addIntegrationError,
  isGetAssistantProfileError,
  getAssistantProfileError,
} = useAssistant()

const {
  getCredentials,
  saveCredentials,
  getAuthorizationUrl,
  checkStatus,
  isConnected,
  isLoading,
  savedClientId,
  savedRedirectUri,
  hasSecret,
  isSaveCredentialsError,
  saveCredentialsError,
  isGetAuthUrlError,
  getAuthUrlError,
  isCheckStatusError,
  checkStatusError,
} = useCalendar()

const { openOAuthPopup } = useOAuthPopup()

const credentials = reactive({
  clientId: '',
  clientSecret: '',
  redirectUri: '',
})
const credentialsSaved = ref(false)

const handleSaveCredentials = async () => {
  if (!credentials.clientId || !credentials.clientSecret) {
    toast.add({
      severity: 'warn',
      summary: 'Campos requeridos',
      detail: 'Client ID y Client Secret son obligatorios',
      life: 3000,
    })
    return
  }
  try {
    await saveCredentials(
      credentials.clientId,
      credentials.clientSecret,
      credentials.redirectUri || undefined,
    )
    credentialsSaved.value = true
    toast.add({
      severity: 'success',
      summary: 'Credenciales guardadas',
      detail: 'Las credenciales de Google OAuth se guardaron correctamente',
      life: 3000,
    })
  } catch {
    // handled by errorWatchers
  }
}

const errorWatchers = [
  {
    flag: isSaveCredentialsError,
    summary: 'Error al guardar credenciales',
    detail: saveCredentialsError,
  },
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
  {
    flag: isGetAuthUrlError,
    summary: 'Error al obtener URL de autorización',
    detail: getAuthUrlError,
  },
  {
    flag: isCheckStatusError,
    summary: 'Error al verificar estado',
    detail: checkStatusError,
  },
]

const { toast } = useErrorToast(errorWatchers)

const calendarIntegration = reactive<IntegrationParams>({
  name: 'google_calendar',
  type: 'calendar',
  activated: false,
  config: {
    profile_id: '',
    is_connected: false,
  } as GoogleCalendarIntegrationConfig,
})

const connectGoogleCalendar = async () => {
  try {
    // Get the profile_id from the assistant profile
    if (!assistantProfile.value?.id) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudo obtener el ID del perfil',
        life: 3000,
      })
      return
    }

    const config = calendarIntegration.config as GoogleCalendarIntegrationConfig
    config.profile_id = assistantProfile.value.id

    // Get authorization URL
    const authData = await getAuthorizationUrl(config.profile_id)

    if (authData && authData.authorization_url) {
      openOAuthPopup(authData.authorization_url, async () => {
        await checkConnectionStatus()
      })
    } else {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'No se pudo obtener la URL de autorización',
        life: 3000,
      })
    }
  } catch (error) {
    console.error('Error al conectar Google Calendar:', error)
  }
}

const updateIntegration = async () => {
  try {
    await addIntegration(calendarIntegration)
    await getAssistantProfile()
  } catch (error) {
    console.error('Error al actualizar integración:', error)
  }
}

watch(
  () => calendarIntegration.activated,
  async () => {
    await updateIntegration()
  },
)

const searchCalendarIntegration = computed(() => {
  return assistantProfile.value?.integrations?.find(
    (integration) => integration.name === 'google_calendar',
  )
})

const checkConnectionStatus = async () => {
  if (!assistantProfile.value?.id) return

  try {
    const wasConnected = isConnected.value
    await checkStatus(assistantProfile.value.id)
    if (!wasConnected && isConnected.value) {
      // Auto-activate integration when OAuth connection is confirmed
      calendarIntegration.activated = true
      const config = calendarIntegration.config as GoogleCalendarIntegrationConfig
      config.profile_id = assistantProfile.value.id
      config.is_connected = true
      await addIntegration(calendarIntegration)
      toast.add({
        severity: 'success',
        summary: '¡Conectado!',
        detail: 'Google Calendar conectado correctamente',
        life: 4000,
      })
    }
  } catch (error) {
    console.error('Error al verificar estado de conexión:', error)
  }
}

onMounted(async () => {
  await Promise.all([getAssistantProfile(), getCredentials()])

  assistantProfile.value?.integrations?.forEach((integration) => {
    if (integration.name === 'google_calendar') {
      calendarIntegration.activated = integration.activated || false
      const config = calendarIntegration.config as GoogleCalendarIntegrationConfig
      const integrationConfig = integration.config as unknown as GoogleCalendarIntegrationConfig

      config.profile_id = integrationConfig.profile_id || assistantProfile.value?.id || ''
      config.is_connected = integrationConfig.is_connected || false
    }
  })

  // Check connection status
  await checkConnectionStatus()

  // Handle OAuth callback parameters
  if (route.query.success === 'true') {
    toast.add({
      severity: 'success',
      summary: '¡Conexión exitosa!',
      detail: 'Tu cuenta de Google Calendar ha sido conectada correctamente',
      life: 5000,
    })
    // Check status again to update UI
    await checkConnectionStatus()
    // Clean URL
    router.replace({ query: {} })
  } else if (route.query.error) {
    const errorMessages: Record<string, string> = {
      invalid_request: 'Solicitud inválida. Por favor, intenta nuevamente.',
      auth_failed: 'Falló la autorización con Google. Por favor, intenta nuevamente.',
    }
    const errorDetail =
      errorMessages[route.query.error as string] ||
      'Ocurrió un error al conectar con Google Calendar'

    toast.add({
      severity: 'error',
      summary: 'Error de conexión',
      detail: errorDetail,
      life: 5000,
    })
    // Clean URL
    router.replace({ query: {} })
  }
})
</script>

<template>
  <div class="integration-container">
    <!-- Header Section -->
    <div class="header-section">
      <div class="integration-header">
        <div class="icon-wrapper calendar-icon">
          <i class="pi pi-calendar"></i>
        </div>
        <div class="header-content">
          <h1 class="integration-title">Integración Google Calendar</h1>
          <p class="integration-subtitle">Conecta tu asistente con Google Calendar</p>
        </div>
      </div>

      <div class="activation-toggle">
        <div class="toggle-content">
          <div class="toggle-info">
            <span class="toggle-label">Estado de la integración</span>
            <span class="toggle-status" :class="{ active: calendarIntegration.activated }">
              {{ calendarIntegration.activated ? 'Activa' : 'Inactiva' }}
            </span>
          </div>
          <InputSwitch v-model="calendarIntegration.activated" class="modern-switch" />
        </div>
      </div>
    </div>

    <!-- Credentials Card -->
    <Card class="config-card credentials-card">
      <template #content>
        <div class="credentials-section">
          <div class="credentials-header">
            <i class="pi pi-key credentials-icon"></i>
            <div>
              <h3 class="credentials-title">Credenciales OAuth</h3>
              <p class="credentials-subtitle">
                Ingresa las credenciales de tu proyecto en Google Cloud Console
              </p>
            </div>
          </div>

          <div class="credentials-form">
            <div v-if="savedClientId && !credentialsSaved" class="saved-credentials-info">
              <i class="pi pi-check-circle"></i>
              Credenciales configuradas — Client ID: <strong>{{ savedClientId }}</strong>
            </div>

            <div class="field">
              <label class="field-label">Client ID <span class="required">*</span></label>
              <InputText
                v-model="credentials.clientId"
                :placeholder="savedClientId || 'xxxxxxxx.apps.googleusercontent.com'"
                class="field-input"
              />
            </div>

            <div class="field">
              <label class="field-label">Client Secret <span class="required">*</span></label>
              <Password
                v-model="credentials.clientSecret"
                :placeholder="hasSecret ? '••••••••••••• (ya configurado)' : 'GOCSPX-...'"
                class="field-input"
                :feedback="false"
                toggleMask
              />
            </div>

            <div class="field">
              <label class="field-label">
                Redirect URI
                <span class="field-hint">(opcional)</span>
              </label>
              <InputText
                v-model="credentials.redirectUri"
                :placeholder="
                  savedRedirectUri || 'http://localhost:8000/api/v1/calendar/oauth/callback'
                "
                class="field-input"
              />
            </div>

            <div class="credentials-actions">
              <Button
                label="Guardar Credenciales"
                icon="pi pi-save"
                severity="primary"
                :loading="isLoading"
                :disabled="
                  (!credentials.clientId && !savedClientId) ||
                  (!credentials.clientSecret && !hasSecret)
                "
                @click="handleSaveCredentials"
              />
              <span v-if="credentialsSaved" class="saved-badge">
                <i class="pi pi-check-circle"></i> Guardado
              </span>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Connection Card -->
    <Card class="config-card" :class="{ 'card-disabled': !calendarIntegration.activated }">
      <template #content>
        <div class="connection-section">
          <div class="connection-status">
            <div class="status-indicator">
              <i
                class="pi"
                :class="isConnected ? 'pi-check-circle' : 'pi-times-circle'"
                :style="{
                  color: isConnected ? 'var(--color-success)' : 'var(--color-danger)',
                }"
              ></i>
              <span class="status-text">
                {{ isConnected ? 'Conectado a Google Calendar' : 'No conectado' }}
              </span>
            </div>

            <div v-if="!isConnected" class="connection-info">
              <Message severity="info" :closable="false">
                <p>
                  Para utilizar esta integración, necesitas autorizar el acceso a tu cuenta de
                  Google Calendar. Haz clic en el botón "Conectar con Google" para comenzar.
                </p>
              </Message>
            </div>

            <div v-else class="connection-info">
              <Message severity="success" :closable="false">
                <p>
                  Tu cuenta de Google Calendar está conectada correctamente. Ahora puedes crear,
                  actualizar y gestionar eventos desde el asistente.
                </p>
              </Message>
            </div>
          </div>

          <div class="connection-actions">
            <Button
              v-if="!isConnected"
              label="Conectar con Google"
              icon="pi pi-google"
              severity="primary"
              size="large"
              :disabled="!calendarIntegration.activated"
              @click="connectGoogleCalendar"
            />
            <div v-else class="connected-actions">
              <Button
                label="Verificar Conexión"
                icon="pi pi-refresh"
                severity="secondary"
                @click="checkConnectionStatus"
              />
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Information Card -->
    <Card class="info-card">
      <template #header>
        <div class="info-header">
          <i class="pi pi-info-circle info-icon"></i>
          <span class="info-title">Información</span>
        </div>
      </template>
      <template #content>
        <div class="info-grid">
          <div class="info-item">
            <div class="info-label">
              <i class="pi pi-shield"></i>
              Permisos requeridos
            </div>
            <div class="info-value">Gestión de eventos de calendario</div>
          </div>

          <div class="info-item">
            <div class="info-label">
              <i class="pi pi-clock"></i>
              Sincronización
            </div>
            <div class="info-value">Bidireccional en tiempo real</div>
          </div>

          <div class="info-item">
            <div class="info-label">
              <i class="pi pi-check"></i>
              Estado de conexión
            </div>
            <div class="info-value">
              {{
                isConnected
                  ? 'Conectado'
                  : searchCalendarIntegration
                    ? 'Configurado pero no conectado'
                    : 'No configurado'
              }}
            </div>
          </div>
        </div>

        <div class="capabilities-section">
          <h3 class="capabilities-title">Capacidades</h3>
          <ul class="capabilities-list">
            <li><i class="pi pi-check"></i> Crear eventos de calendario desde el chat</li>
            <li><i class="pi pi-check"></i> Listar eventos próximos</li>
            <li><i class="pi pi-check"></i> Actualizar eventos existentes</li>
            <li><i class="pi pi-check"></i> Eliminar eventos</li>
            <li><i class="pi pi-check"></i> Añadir asistentes y recordatorios</li>
            <li><i class="pi pi-check"></i> Sincronización automática con Google Calendar</li>
          </ul>
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
  background: var(--do-bg);
  box-sizing: border-box;
}

/* Header Section */
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

.calendar-icon {
  background: linear-gradient(135deg, #4285f4 0%, #34a853 100%);
}

.header-content {
  flex: 1;
}

.integration-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 0.25rem 0;
  color: var(--do-text);
}

.integration-subtitle {
  font-size: 0.95rem;
  color: var(--do-text-muted);
  margin: 0;
  font-weight: 400;
}

/* Activation Toggle */
.activation-toggle {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 0.75rem;
  padding: 1rem;
  box-shadow: 0 3px 14px rgba(0, 0, 0, 0.06);
  border: 1px solid var(--vt-c-gray-200);
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
  color: var(--do-text);
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

/* Credentials Card */
.credentials-section {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.credentials-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.credentials-icon {
  font-size: 1.4rem;
  color: var(--color-primary);
}

.credentials-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--do-text);
  margin: 0 0 0.2rem;
}

.credentials-subtitle {
  font-size: 0.85rem;
  color: var(--do-text-muted);
  margin: 0;
}

.saved-credentials-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--color-success);
  background: rgba(34, 197, 94, 0.08);
  border: 1px solid rgba(34, 197, 94, 0.25);
  border-radius: 0.5rem;
  padding: 0.6rem 0.75rem;
}

.credentials-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.field-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--do-text-secondary);
}

.field-hint {
  font-weight: 400;
  color: var(--do-text-muted);
}

.required {
  color: var(--color-danger);
}

.field-input {
  width: 100%;
}

:deep(.field-input.p-password) {
  width: 100%;
}

:deep(.field-input.p-password .p-inputtext) {
  width: 100%;
}

.credentials-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-top: 0.25rem;
}

.saved-badge {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-success);
}

/* Connection Card */
.config-card {
  margin-bottom: 1.25rem;
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--vt-c-gray-200);
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
  padding: 1.5rem;
}

.connection-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.connection-status {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.1rem;
  font-weight: 600;
}

.status-indicator i {
  font-size: 1.5rem;
}

.connection-info {
  margin-top: 0.5rem;
}

.connection-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
}

.connected-actions {
  display: flex;
  gap: 1rem;
}

/* Information Card */
.info-card {
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--vt-c-gray-200);
}

:deep(.info-card .p-card-header) {
  background: rgba(255, 255, 255, 0.04);
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--vt-c-gray-200);
}

.info-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.info-icon {
  color: var(--color-primary);
  font-size: 1.125rem;
}

.info-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--do-text);
}

:deep(.info-card .p-card-content) {
  padding: 1rem;
}

.info-grid {
  display: grid;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 0.6rem;
  border: 1px solid var(--vt-c-gray-200);
}

.info-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--do-text-muted);
}

.info-label i {
  color: var(--color-primary);
}

.info-value {
  font-size: 0.95rem;
  color: var(--do-text);
  padding-left: 1.5rem;
}

.capabilities-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--vt-c-gray-200);
}

.capabilities-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--do-text);
  margin-bottom: 0.75rem;
}

.capabilities-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.capabilities-list li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--do-text-muted);
}

.capabilities-list li i {
  color: var(--color-success);
  font-size: 0.75rem;
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

  .connection-actions,
  .connected-actions {
    flex-direction: column;
    width: 100%;
  }

  .connection-actions :deep(button),
  .connected-actions :deep(button) {
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
}

@media (min-width: 992px) {
  .integration-container {
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 1rem;
    align-items: start;
  }

  .header-section {
    grid-column: 1 / 3;
  }

  .credentials-card,
  .config-card {
    grid-column: 1 / 2;
  }

  .info-card {
    grid-column: 2 / 3;
    grid-row: 2 / 4;
    position: sticky;
    top: 5.2rem;
    align-self: start;
  }
}
</style>
