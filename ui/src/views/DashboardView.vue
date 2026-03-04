<script setup lang="ts">
import { ref, reactive, watch, computed, onMounted } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import LoadingSpinner from '@/components/core/LoadingSpinner/LoadingSpinner.vue'
import DefaultModal from '@/components/core/shared/DefaultModal/DefaultModal.vue'
import ScrollPanel from 'primevue/scrollpanel'
import Toast from 'primevue/toast'
import type { AssistantProfileParams, AssistantProfileUpdateParams } from '@/types/assistant.ts'
import { useToogle } from '@/composables/useToogle'
import { useAssistant } from '@/composables/useAssistant'
import { useConversation } from '@/composables/useConversation'
import { useErrorToast } from '@/composables/useErrorToast'

const { toogleValue: isVisible } = useToogle(false)
const { toogleValue: isVisibleUpdate } = useToogle(false)

const {
  conversations,
  getUserConversation,
  isGetUserConversationError,
  isGetUserConversationSuccess,
  getUserConversationError,
} = useConversation()

const {
  addAssistantProfile,
  getAssistantProfile,
  updateAssistantProfile,

  isAddAssistantProfilePending,
  isAddAssistantProfileSuccess,
  isAddAssistantProfileError,
  addAssistantProfileError,

  isGetAssistantProfileSuccess,
  isGetAssistantProfileError,
  getAssistantProfileError,
  isGetAssistantProfilePending,

  isUpdateAssistantProfilePending,
  isUpdateAssistantProfileSuccess,
  isUpdateAssistantProfileError,
  updateAssistantProfileError,

  assistantProfile,
} = useAssistant()

const errorWatchers = [
  {
    flag: isAddAssistantProfileError,
    summary: 'Error al agregar asistente',
    detail: addAssistantProfileError,
  },
  {
    flag: isUpdateAssistantProfileError,
    summary: 'Error al actualizar asistente',
    detail: updateAssistantProfileError,
  },
  {
    flag: isGetAssistantProfileError,
    summary: 'Error al obtener perfil de asistente',
    detail: getAssistantProfileError,
  },
  {
    flag: isGetUserConversationError,
    summary: 'Error al obtener conversaciones',
    detail: getUserConversationError,
  },
]

const { toast } = useErrorToast(errorWatchers)

onMounted(async () => {
  try {
    await getAssistantProfile()
    if (isGetAssistantProfileSuccess.value) {
      await getUserConversation()
    }
  } catch (error) {
    console.error('Error loading dashboard data:', error)
  }
})

const modalTitle = ref('Agregar Asistente')
const changeVisible = (value: boolean) => {
  isVisible.value = value
}

const assistantProfileParams = reactive<AssistantProfileParams>({
  assistant_name: '',
  business_name: '',
  functions: '',
  business_context: '',
})

const addAssistant = async () => {
  await addAssistantProfile(assistantProfileParams)
  if (isAddAssistantProfileSuccess.value) {
    await getAssistantProfile()
    toast.add({
      severity: 'success',
      summary: 'Asistente agregado',
      detail: 'El asistente se creó correctamente',
      life: 3000,
    })
  }
  isVisible.value = false
}

const modalTitleUpdate = ref('Editar Asistente')
const updateAssistantProfileParams = reactive<AssistantProfileUpdateParams>({
  assistant_name: '',
  business_name: '',
  functions: '',
  business_context: '',
})

const changeUpdateVisible = (value: boolean) => {
  isVisibleUpdate.value = value
}

const updateAssistan = async () => {
  await updateAssistantProfile(updateAssistantProfileParams)
  if (isUpdateAssistantProfileSuccess.value) {
    await getAssistantProfile()
    toast.add({
      severity: 'success',
      summary: 'Asistente actualizado',
      detail: 'El asistente se actualizó correctamente',
      life: 3000,
    })
  }
  isVisibleUpdate.value = false
}

watch(
  isVisibleUpdate,
  () => {
    if (assistantProfile && isVisibleUpdate.value) {
      updateAssistantProfileParams.assistant_name = assistantProfile?.value?.assistant_name || ''
      updateAssistantProfileParams.business_name = assistantProfile?.value?.business_name || ''
      updateAssistantProfileParams.functions = assistantProfile?.value?.functions || ''
      updateAssistantProfileParams.business_context =
        assistantProfile?.value?.business_context || ''
    }
  },
  { immediate: true },
)

const totalMessagesInConversation = computed(() => {
  return conversations.value?.reduce((acc, curr) => {
    return acc + (curr?.messages?.length || 0)
  }, 0)
})

const integrations = [
  {
    name: 'Storage',
    description: 'Integración con almacenamiento de archivos en la nube',
    icon: 'pi pi-file',
    tone: 'primary',
    to: 'store-integration',
    enabled: true,
  },
  {
    name: 'WhatsApp (Meta API)',
    description: 'Integración WhatsApp con Meta Business API oficial',
    icon: 'pi pi-whatsapp',
    tone: 'success',
    to: 'whatsapp-integration',
    enabled: true,
  },
  {
    name: 'WhatsApp Devices',
    description: 'Gestión de dispositivos WhatsApp con respuestas automáticas de IA',
    icon: 'pi pi-whatsapp',
    tone: 'success',
    to: 'whatsapp-devices',
    enabled: true,
  },
  {
    name: 'Mercado Libre',
    description: 'Integración Mercado Libre, Contestar preguntas sin responder',
    icon: 'pi pi-chat',
    tone: 'warning',
    to: 'meli-integration',
    enabled: false,
  },
  {
    name: 'Google Calendar',
    description: 'Integración Google Calendar, gestiona eventos y sincronización',
    icon: 'pi pi-calendar',
    tone: 'warning',
    to: 'google-calendar-integration',
    enabled: true,
  },
  {
    name: 'Google Drive',
    description: 'Integración Google Drive, accede a documentos y archivos desde el asistente',
    icon: 'pi pi-folder-open',
    tone: 'info',
    to: 'google-drive-integration',
    enabled: true,
  },
  {
    name: 'Base de Datos SQL',
    description: 'Conecta el asistente a una tabla de PostgreSQL para consultar datos en tiempo real',
    icon: 'pi pi-database',
    tone: 'info',
    to: 'sqldatabase-integration',
    enabled: true,
  },
  {
    name: 'Prompts de Tools',
    description: 'Personaliza las instrucciones de cada tool del asistente (cuándo y cómo usarlas)',
    icon: 'pi pi-sliders-h',
    tone: 'primary',
    to: 'tool-prompts',
    enabled: true,
  },
  {
    name: 'Funciones',
    description: 'Editor de funciones personalizadas para el asistente',
    icon: 'pi pi-code',
    tone: 'primary',
    to: 'functions',
    enabled: true,
  },
]
</script>

<template>
  <div class="dashboard-container">
    <!-- Header Section -->
    <div class="dashboard-header">
      <div class="header-content">
        <div class="icon-wrapper">
          <i class="pi pi-th-large"></i>
        </div>
        <div class="title-section">
          <h1 class="dashboard-title">Dashboard</h1>
          <p class="dashboard-subtitle">Gestiona tu asistente y revisa el rendimiento</p>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="content-grid">
      <!-- Assistant Profile Section -->
      <div class="profile-section">
        <!-- Loading State -->
        <div v-if="isGetAssistantProfilePending" class="loading-card">
          <Card>
            <template #content>
              <div class="loading-state">
                <LoadingSpinner />
                <p>Cargando perfil del asistente...</p>
              </div>
            </template>
          </Card>
        </div>

        <!-- No Assistant State -->
        <div v-else-if="!assistantProfile" class="empty-card">
          <Card>
            <template #content>
              <div class="empty-state">
                <i class="pi pi-robot"></i>
                <h3>No hay asistente configurado</h3>
                <p>Crea tu primer asistente para comenzar</p>
                <Button
                  label="Crear Asistente"
                  icon="pi pi-plus"
                  class="create-button"
                  @click="isVisible = true"
                />
              </div>
            </template>
          </Card>
        </div>

        <!-- Assistant Profile Card -->
        <Card v-else class="profile-card p-2">
          <template #header>
            <div class="profile-header">
              <div class="profile-info">
                <div class="profile-icon">
                  <i class="pi pi-sparkles"></i>
                </div>
                <div class="profile-details">
                  <h3>{{ assistantProfile?.assistant_name }}</h3>
                  <p>Asistente Virtual</p>
                </div>
              </div>
              <Button
                icon="pi pi-pencil"
                class="edit-button"
                size="small"
                @click="isVisibleUpdate = true"
                title="Editar asistente"
              />
            </div>
          </template>
          <template #content>
            <div class="profile-content">
              <div class="info-item">
                <label>Empresa</label>
                <span>{{ assistantProfile?.business_name }}</span>
              </div>
              <div class="info-item">
                <label>Contexto de Negocio</label>
                <ScrollPanel class="context-scroll">
                  <p>{{ assistantProfile?.business_context }}</p>
                </ScrollPanel>
              </div>
              <div class="profile-actions">
                <RouterLink class="sandbox-button" :to="{ name: 'sandbox' }">
                  <i class="pi pi-shield"></i>
                  Sandbox Testing
                </RouterLink>
              </div>
            </div>
          </template>
        </Card>

        <!-- Integrations (moved up) -->
        <div class="integrations-section">
          <div class="section-header">
            <h2>Integraciones Disponibles</h2>
            <p>Conecta tu asistente con diferentes plataformas</p>
          </div>

          <div class="integrations-grid">
            <button
              v-for="integration in integrations"
              :key="integration.name"
              type="button"
              class="integration-button"
              :class="{ 'is-disabled': !integration.enabled }"
              :disabled="!integration.enabled"
              @click="integration.enabled && $router.push({ name: integration.to })"
            >
              <div class="integration-content">
                <div class="integration-main">
                  <div
                    class="integration-icon"
                    :class="integration.enabled ? `tone-${integration.tone}` : 'disabled'"
                  >
                    <i :class="integration.icon"></i>
                  </div>
                  <div class="integration-info">
                    <h3>{{ integration.name }}</h3>
                  </div>
                </div>

                <div class="integration-actions">
                  <span v-if="integration.enabled" class="integration-action-label">Configurar</span>
                  <span v-else class="integration-action-label">Próximamente</span>
                </div>

                <div class="integration-legend">{{ integration.description }}</div>
              </div>
            </button>
          </div>
        </div>
      </div>

      <!-- Stats Card (moved down) -->
      <Card v-if="isGetUserConversationSuccess" class="stats-card p-2">
        <template #header>
          <div class="stats-header">
            <div class="stats-icon">
              <i class="pi pi-chart-bar"></i>
            </div>
            <div class="stats-info">
              <h3>Estadísticas</h3>
              <p>Resumen de actividad</p>
            </div>
          </div>
        </template>
        <template #content>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-value">{{ conversations?.length || 0 }}</div>
              <div class="stat-label">Conversaciones</div>
              <div class="stat-icon">
                <i class="pi pi-comments"></i>
              </div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ totalMessagesInConversation || 0 }}</div>
              <div class="stat-label">Mensajes</div>
              <div class="stat-icon">
                <i class="pi pi-envelope"></i>
              </div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ assistantProfile?.iteration_limit || 0 }}</div>
              <div class="stat-label">Iteraciones Restantes</div>
              <div class="stat-icon">
                <i class="pi pi-clock"></i>
              </div>
            </div>
          </div>
          <div class="stats-actions">
            <RouterLink class="view-conversations-button" :to="{ name: 'conversation' }">
              <i class="pi pi-eye"></i>
              Ver Conversaciones
            </RouterLink>
          </div>
        </template>
      </Card>
    </div>

    <!-- Modals -->
    <DefaultModal :isVisible="isVisible" :title="modalTitle" @update:visible="changeVisible">
      <form @submit.prevent="addAssistant" class="modal-form">
        <div class="form-field">
          <label for="assistant_name">Nombre del Asistente</label>
          <InputText
            id="assistant_name"
            v-model="assistantProfileParams.assistant_name"
            placeholder="Ingresa el nombre del asistente"
            required
          />
        </div>

        <div class="form-field">
          <label for="business_name">Nombre de la Empresa</label>
          <InputText
            id="business_name"
            v-model="assistantProfileParams.business_name"
            placeholder="Ingresa el nombre de la empresa"
            required
          />
        </div>

        <div class="form-field">
          <label for="business_context">Contexto del Negocio</label>
          <Textarea
            id="business_context"
            v-model="assistantProfileParams.business_context"
            placeholder="Describe el contexto de tu negocio"
            rows="4"
            required
          />
        </div>

        <div class="modal-actions">
          <Button
            type="button"
            label="Cancelar"
            severity="secondary"
            @click="() => changeVisible(false)"
          />
          <Button type="submit" label="Crear Asistente" :loading="isAddAssistantProfilePending" />
        </div>
      </form>
    </DefaultModal>

    <DefaultModal
      :isVisible="isVisibleUpdate"
      :title="modalTitleUpdate"
      @update:visible="changeUpdateVisible"
    >
      <form @submit.prevent="updateAssistan" class="modal-form">
        <div class="form-field">
          <label for="update_assistant_name">Nombre del Asistente</label>
          <InputText
            id="update_assistant_name"
            v-model="updateAssistantProfileParams.assistant_name"
            placeholder="Ingresa el nombre del asistente"
            required
          />
        </div>

        <div class="form-field">
          <label for="update_business_name">Nombre de la Empresa</label>
          <InputText
            id="update_business_name"
            v-model="updateAssistantProfileParams.business_name"
            placeholder="Ingresa el nombre de la empresa"
            required
          />
        </div>

        <div class="form-field">
          <label for="update_business_context">Contexto del Negocio</label>
          <Textarea
            id="update_business_context"
            v-model="updateAssistantProfileParams.business_context"
            placeholder="Describe el contexto de tu negocio"
            rows="4"
            required
          />
        </div>

        <div class="modal-actions">
          <Button
            type="button"
            label="Cancelar"
            severity="secondary"
            @click="() => changeUpdateVisible(false)"
          />
          <Button
            type="submit"
            label="Actualizar Asistente"
            :loading="isUpdateAssistantProfilePending"
          />
        </div>
      </form>
    </DefaultModal>
  </div>

  <Toast />
</template>

<style scoped>
/* Dashboard Container */
.dashboard-container {
  padding: 1rem;
  padding-top: calc(3.25rem + 0.9rem);
  min-height: 100vh;
  background: var(--do-bg);
}

/* Header Section */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--do-bg-white);
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 4px var(--shadow-light);
  border: 1px solid var(--do-border-light);
  margin-bottom: 1rem;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.icon-wrapper {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.55rem;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1rem;
  box-shadow: 0 4px 14px var(--shadow-light);
}

.title-section {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.dashboard-title {
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--do-text);
  margin: 0;
  line-height: 1.2;
}

.dashboard-subtitle {
  font-size: 0.85rem;
  color: var(--do-text-muted);
  margin: 0;
  line-height: 1.5;
}

/* Content Grid */
.content-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1rem;
}

/* Profile Section */
.profile-section {
  display: flex;
  flex-direction: row;
  gap: 0.85rem;
  align-items: flex-start;
}

.profile-section > * {
  flex: 1;
  min-width: 0;
}

.section-header {
  text-align: center;
  margin-bottom: 0.85rem;
}

.section-header h2 {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--do-text);
  margin-bottom: 0.4rem;
}

.section-header p {
  font-size: 0.85rem;
  color: var(--do-text-muted);
  line-height: 1.6;
}

.integrations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
}

/* Profile Card */
.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.profile-info {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.profile-icon {
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  background: var(--gradient-success);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--vt-c-white);
  font-size: 0.85rem;
}

.profile-details h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0 0 0.25rem 0;
}

.profile-details p {
  color: var(--do-text-muted);
  margin: 0;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-item label {
  font-weight: 600;
  color: var(--do-text-secondary);
  font-size: 0.875rem;
}

.info-item span {
  color: var(--do-text);
  font-size: 1rem;
}

.context-scroll {
  max-height: 110px;
}

.context-scroll p {
  margin: 0;
  color: var(--do-text-muted);
  line-height: 1.6;
}

.profile-actions {
  margin-top: 0.65rem;
  padding-top: 0.65rem;
  border-top: 1px solid var(--do-border-light);
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.sandbox-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  color: var(--vt-c-white);
  text-decoration: none;
  border-radius: 0.5rem;
  font-weight: 600;
  font-size: 0.8rem;
  transition: all 0.3s ease;
  flex: 1;
  justify-content: center;
  min-width: fit-content;
}

.sandbox-button {
  background: var(--gradient-warning);
  box-shadow: 0 4px 14px var(--shadow-light);
}

.sandbox-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px var(--shadow-medium);
  color: var(--vt-c-white);
}

.sandbox-button i {
  font-size: 1.1rem;
}

/* Stats Card */
.stats-header {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.stats-icon {
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 0.85rem;
}

.stats-info h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0 0 0.25rem 0;
}

.stats-info p {
  color: var(--do-text-muted);
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.7rem;
  margin-bottom: 0.85rem;
}

.stat-item {
  text-align: center;
  padding: 0.65rem;
  background: var(--vt-c-gray-50);
  border-radius: 0.5rem;
  border: 1px solid var(--do-border-light);
  position: relative;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--do-text);
  margin-bottom: 0.2rem;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--do-text-muted);
  font-weight: 500;
}

.stat-icon {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  color: var(--do-blue);
  font-size: 1rem;
}

.stats-actions {
  text-align: center;
}

.view-conversations-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--gradient-primary);
  color: var(--vt-c-white);
  text-decoration: none;
  border-radius: 0.5rem;
  font-weight: 600;
  font-size: 0.8rem;
  transition: all 0.3s ease;
  box-shadow: 0 4px 14px var(--shadow-light);
}

.view-conversations-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px var(--shadow-medium);
  color: var(--vt-c-white);
}

/* Integration Buttons */
.integration-button {
  position: relative;
  border: 1px solid var(--do-border);
  background: var(--do-bg-white);
  width: 100%;
  text-align: left;
  padding: 0.55rem 0.7rem;
  border-radius: 0.5rem;
  cursor: pointer;
  font-family: inherit;
  min-height: 52px;
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast),
    transform var(--transition-fast);
}

.integration-button:not(.is-disabled):hover,
.integration-button:not(.is-disabled):focus-visible {
  border-color: var(--do-blue);
  box-shadow: 0 3px 10px var(--shadow-light);
  outline: none;
}

.integration-button.is-disabled {
  cursor: not-allowed;
  opacity: 0.85;
}

.integration-button.is-disabled:hover {
  transform: none;
}

.integration-content {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 0.5rem;
}

.integration-main {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

.integration-actions {
  display: flex;
}

.integration-action-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--do-text-secondary);
  border: 1px solid var(--do-border-light);
  background: var(--vt-c-gray-50);
  border-radius: 999px;
  padding: 0.15rem 0.45rem;
}

.integration-button.is-disabled .integration-action-label {
  color: var(--do-text-muted);
}

.integration-legend {
  position: absolute;
  left: 0.875rem;
  right: 0.875rem;
  bottom: calc(100% + 0.5rem);
  background: var(--do-navy);
  color: var(--vt-c-white);
  padding: 0.5rem 0.625rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  line-height: 1.3;
  opacity: 0;
  visibility: hidden;
  transform: translateY(4px);
  transition: all var(--transition-fast);
  pointer-events: none;
  box-shadow: 0 6px 14px var(--shadow-medium);
  z-index: 2;
}

.integration-legend::after {
  content: '';
  position: absolute;
  left: 1rem;
  top: 100%;
  border-width: 6px;
  border-style: solid;
  border-color: var(--do-navy) transparent transparent transparent;
}

.integration-button:hover .integration-legend,
.integration-button:focus-visible .integration-legend {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.integration-icon {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.4rem;
  background: var(--do-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  border: 1px solid var(--do-border-light);
}

.integration-icon.tone-primary {
  color: var(--do-blue);
  background: var(--vt-c-gray-50);
}

.integration-icon.tone-success {
  color: var(--do-success);
  background: var(--vt-c-gray-50);
}

.integration-icon.tone-warning {
  color: var(--do-warning);
  background: var(--vt-c-gray-50);
}

.integration-icon.tone-info {
  color: var(--do-info);
  background: var(--vt-c-gray-50);
}

.integration-icon.disabled {
  color: var(--do-text-muted);
  background: var(--vt-c-gray-100);
}

.integration-info h3 {
  margin: 0;
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--do-text);
  line-height: 1.2;
}

/* Loading and Empty States */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  text-align: center;
  padding: 1rem;
}

.loading-state p,
.empty-state p {
  color: var(--do-text-muted);
  margin: 0;
}

.empty-state i {
  font-size: 2rem;
  color: var(--do-blue);
}

.empty-state h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--do-text);
  margin: 0;
}

.create-button {
  background: var(--gradient-success);
  border: none;
  color: var(--vt-c-white);
  padding: 0.55rem 0.8rem;
  border-radius: 0.5rem;
  font-weight: 600;
  font-size: 0.82rem;
  transition: all 0.3s ease;
  box-shadow: 0 4px 14px var(--shadow-light);
}

.create-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px var(--shadow-medium);
}

/* Modal Styles */
.modal-form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  margin-bottom: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  font-weight: 600;
  color: var(--do-text-secondary);
  font-size: 0.875rem;
}

:deep(.form-field .p-inputtext),
:deep(.form-field .p-inputtextarea) {
  border: 2px solid var(--do-border-light);
  border-radius: 0.5rem;
  padding: 0.55rem;
  transition: all 0.3s ease;
}

:deep(.form-field .p-inputtext:focus),
:deep(.form-field .p-inputtextarea:focus) {
  border-color: var(--do-blue);
  box-shadow: 0 0 0 3px var(--vt-c-gray-200);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  padding-top: 0.65rem;
  border-top: 1px solid var(--do-border-light);
}

/* Responsive Design */
@media (max-width: 768px) {
  .dashboard-container {
    padding: 0.85rem;
    padding-top: calc(3.25rem + 0.7rem);
  }

  .dashboard-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
    padding: 0.85rem;
  }

  .header-content {
    flex-direction: column;
    gap: 1rem;
  }

  .dashboard-title {
    font-size: 1.2rem;
  }

  .dashboard-subtitle {
    font-size: 0.82rem;
  }

  .profile-section {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .integrations-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .section-header h2 {
    font-size: 1.1rem;
  }

  .section-header p {
    font-size: 0.82rem;
  }
}

@media (max-width: 480px) {
  .dashboard-container {
    padding: 0.6rem;
    padding-top: calc(3.25rem + 0.6rem);
  }

  .icon-wrapper {
    width: 2.2rem;
    height: 2.2rem;
    font-size: 0.9rem;
  }

  .dashboard-title {
    font-size: 1.05rem;
  }

  .dashboard-header {
    padding: 0.75rem;
  }

  :deep(.loading-card .p-card-content),
  :deep(.empty-card .p-card-content),
  :deep(.profile-card .p-card-content),
  :deep(.stats-card .p-card-content) {
    padding: 1.25rem;
  }

  :deep(.profile-card .p-card-header),
  :deep(.stats-card .p-card-header) {
    padding: 1rem 1.25rem;
  }
}
</style>
