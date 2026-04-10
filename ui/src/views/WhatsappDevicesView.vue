<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useWhatsApp } from '@/composables/useWhatsApp'
import { useToast } from 'primevue/usetoast'
import type { WhatsAppDevice } from '@/services/whatsapp'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import ProgressSpinner from 'primevue/progressspinner'
import { useI18n } from 'vue-i18n'

const whatsapp = useWhatsApp()
const toast = useToast()
const { t } = useI18n()

// Country codes
interface Country {
  name: string
  flag: string
  dial: string
}

const countries: Country[] = [
  { name: 'Argentina', flag: '🇦🇷', dial: '+54' },
  { name: 'México', flag: '🇲🇽', dial: '+52' },
  { name: 'Colombia', flag: '🇨🇴', dial: '+57' },
  { name: 'Chile', flag: '🇨🇱', dial: '+56' },
  { name: 'Perú', flag: '🇵🇪', dial: '+51' },
  { name: 'Uruguay', flag: '🇺🇾', dial: '+598' },
  { name: 'Paraguay', flag: '🇵🇾', dial: '+595' },
  { name: 'Bolivia', flag: '🇧🇴', dial: '+591' },
  { name: 'Ecuador', flag: '🇪🇨', dial: '+593' },
  { name: 'Venezuela', flag: '🇻🇪', dial: '+58' },
  { name: 'Brasil', flag: '🇧🇷', dial: '+55' },
  { name: 'España', flag: '🇪🇸', dial: '+34' },
  { name: 'Estados Unidos', flag: '🇺🇸', dial: '+1' },
]

const selectedCountry = ref<Country>(countries[0]) // Argentina
const localPhone = ref('')

const devices = ref<WhatsAppDevice[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const showQRDialog = ref(false)
const qrCode = ref<string>()
const selectedDevice = ref<WhatsAppDevice>()
const wsConnection = ref<WebSocket | null>(null)

function getWsBaseUrl(): string {
  const httpBase =
    import.meta.env.VITE_WHATSAPP_API_BASE_URL || 'http://localhost:8000/api/whatsapp'
  return httpBase.replace(/^https?/, (p: string) => (p === 'https' ? 'wss' : 'ws'))
}

const newDevice = ref({ device_name: '' })

const hasDevices = computed(() => devices.value?.length > 0)

const loadDevices = async () => {
  loading.value = true
  try {
    devices.value = await whatsapp.listDevices()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('integrations.whatsappDevices.errorLoadDevices'),
      life: 3000,
    })
    console.error('Error loading devices:', error)
  } finally {
    loading.value = false
  }
}

const createDevice = async () => {
  if (!localPhone.value || !newDevice.value.device_name) {
    toast.add({
      severity: 'warn',
      summary: t('common.requiredFields'),
      detail: t('common.completeRequired'),
      life: 3000,
    })
    return
  }

  loading.value = true
  try {
    const phone_number = selectedCountry.value.dial + localPhone.value.replace(/^\+/, '')
    const device = await whatsapp.createDevice({ ...newDevice.value, phone_number })
    toast.add({
      severity: 'success',
      summary: t('integrations.whatsappDevices.deviceCreated'),
      detail: `${device.device_name} ${t('integrations.whatsappDevices.deviceCreatedDesc')}`,
      life: 3000,
    })
    showCreateDialog.value = false
    newDevice.value = { device_name: '' }
    localPhone.value = ''
    selectedCountry.value = countries[0]
    await loadDevices()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('integrations.whatsappDevices.errorCreateDevice'),
      life: 3000,
    })
    console.error('Error creating device:', error)
  } finally {
    loading.value = false
  }
}

const connectDevice = async (device: WhatsAppDevice) => {
  loading.value = true
  try {
    // 1. Trigger neonize to start QR generation (async on the backend)
    await whatsapp.authenticateDevice(device.id, { auth_method: 'qr' })

    // 2. Show dialog immediately with loading spinner (QR not yet available)
    selectedDevice.value = device
    qrCode.value = undefined
    showQRDialog.value = true

    // 3. Open WebSocket — backend polls DB and pushes QR when ready
    const ws = new WebSocket(`${getWsBaseUrl()}/device/${device.id}/qr-stream`)
    wsConnection.value = ws

    ws.onmessage = async (event) => {
      const msg = JSON.parse(event.data)

      if (msg.type === 'qr') {
        // Backend sent the QR code as base64 PNG
        qrCode.value = msg.data
      } else if (msg.type === 'authenticated') {
        ws.close()
        wsConnection.value = null
        showQRDialog.value = false
        qrCode.value = undefined

        // 4. Connect device so it starts listening for incoming messages
        try {
          await whatsapp.connectDevice(device.id, 'qr')
        } catch (e) {
          console.warn('Auto-connect after auth:', e)
        }

        toast.add({
          severity: 'success',
          summary: t('integrations.whatsappDevices.deviceAuthenticated'),
          detail: `${device.device_name} ${t('integrations.whatsappDevices.deviceAuthenticatedDesc')}`,
          life: 4000,
        })
        selectedDevice.value = undefined
        await loadDevices()
      } else if (msg.type === 'error') {
        toast.add({
          severity: 'error',
          summary: t('integrations.whatsappDevices.errorAuthTitle'),
          detail: msg.message || t('common.unknownError'),
          life: 4000,
        })
      }
    }

    ws.onerror = () => {
      toast.add({
        severity: 'error',
        summary: t('integrations.whatsappDevices.errorConnTitle'),
        detail: t('integrations.whatsappDevices.errorConnStream'),
        life: 3000,
      })
    }
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('integrations.whatsappDevices.errorConnect'),
      life: 3000,
    })
    console.error('Error connecting device:', error)
  } finally {
    loading.value = false
  }
}

const disconnectDevice = async (device: WhatsAppDevice) => {
  loading.value = true
  try {
    await whatsapp.disconnectDevice(device.id)
    toast.add({
      severity: 'success',
      summary: t('integrations.whatsappDevices.deviceDisconnected'),
      detail: `${device.device_name} ${t('integrations.whatsappDevices.deviceDisconnectedDesc')}`,
      life: 3000,
    })
    await loadDevices()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('integrations.whatsappDevices.errorDisconnect'),
      life: 3000,
    })
    console.error('Error disconnecting device:', error)
  } finally {
    loading.value = false
  }
}

const deleteDevice = async (device: WhatsAppDevice) => {
  if (!confirm(`${t('integrations.whatsappDevices.confirmDelete')} ${device.device_name}?`)) {
    return
  }

  loading.value = true
  try {
    await whatsapp.deleteDevice(device.id)
    toast.add({
      severity: 'success',
      summary: t('integrations.whatsappDevices.deviceDeleted'),
      detail: `${device.device_name} ${t('integrations.whatsappDevices.deviceDeletedDesc')}`,
      life: 3000,
    })
    await loadDevices()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('integrations.whatsappDevices.errorDelete'),
      life: 3000,
    })
    console.error('Error deleting device:', error)
  } finally {
    loading.value = false
  }
}

const getStatusSeverity = (status: string) => {
  const severityMap: Record<string, 'success' | 'info' | 'warning' | 'danger'> = {
    authenticated: 'success',
    connected: 'info',
    connecting: 'warning',
    disconnected: 'danger',
  }
  return severityMap[status] || 'info'
}

const getStatusLabel = (status: string) => {
  const labelMap: Record<string, string> = {
    authenticated: t('integrations.whatsappDevices.statusAuthenticated'),
    connected: t('integrations.whatsappDevices.statusConnected'),
    connecting: t('integrations.whatsappDevices.statusConnecting'),
    disconnected: t('integrations.whatsappDevices.statusDisconnected'),
  }
  return labelMap[status] || status
}

const openCreateDialog = () => {
  newDevice.value = { device_name: '' }
  localPhone.value = ''
  selectedCountry.value = countries[0]
  showCreateDialog.value = true
}

const closeQRDialog = async () => {
  if (wsConnection.value) {
    wsConnection.value.close()
    wsConnection.value = null
  }
  showQRDialog.value = false
  qrCode.value = undefined
  selectedDevice.value = undefined
  await loadDevices()
}

onMounted(() => {
  loadDevices()
})
</script>

<template>
  <div class="devices-view">
    <Toast />

    <!-- Page header -->
    <div class="page-header">
      <div class="header-left">
        <div class="icon-wrapper whatsapp-icon">
          <i class="pi pi-whatsapp"></i>
        </div>
        <div class="header-text">
          <h1 class="page-title">{{ t('integrations.whatsappDevices.title') }}</h1>
          <p class="page-subtitle">{{ t('integrations.whatsappDevices.subtitle') }}</p>
        </div>
      </div>
      <Button
        :label="t('integrations.whatsappDevices.addDevice')"
        icon="pi pi-plus"
        severity="primary"
        :disabled="loading"
        @click="openCreateDialog"
      />
    </div>

    <!-- Devices panel -->
    <div class="panel">
      <!-- Loading state -->
      <div v-if="loading && !hasDevices" class="loading-state">
        <ProgressSpinner style="width: 2.5rem; height: 2.5rem" />
        <p class="loading-text">{{ t('integrations.whatsappDevices.loadingDevices') }}</p>
      </div>

      <!-- Empty state -->
      <div v-else-if="!hasDevices && !loading" class="empty-state">
        <i class="pi pi-mobile empty-icon"></i>
        <p class="empty-title">{{ t('integrations.whatsappDevices.noDevices') }}</p>
        <p class="empty-subtitle">{{ t('integrations.whatsappDevices.noDevicesDesc') }}</p>
      </div>

      <!-- DataTable -->
      <DataTable
        v-if="hasDevices"
        :value="devices"
        :loading="loading"
        stripedRows
        responsiveLayout="scroll"
        :paginator="devices.length > 10"
        :rows="10"
        class="devices-table"
      >
        <Column
          field="device_name"
          :header="t('integrations.whatsappDevices.deviceName')"
          :sortable="true"
        >
          <template #body="{ data }">
            <div class="device-name">
              <i class="pi pi-mobile"></i>
              <span>{{ data.device_name }}</span>
            </div>
          </template>
        </Column>

        <Column
          field="phone_number"
          :header="t('integrations.whatsappDevices.phone')"
          :sortable="true"
        >
          <template #body="{ data }">
            <span class="phone-number">{{ data.phone_number }}</span>
          </template>
        </Column>

        <Column field="status" :header="t('integrations.whatsappDevices.status')" :sortable="true">
          <template #body="{ data }">
            <Tag :severity="getStatusSeverity(data.status)" :value="getStatusLabel(data.status)" />
          </template>
        </Column>

        <Column
          field="last_connected_at"
          :header="t('integrations.whatsappDevices.lastConnection')"
          :sortable="true"
        >
          <template #body="{ data }">
            <span v-if="data.last_connected_at" class="date">
              {{ new Date(data.last_connected_at).toLocaleString() }}
            </span>
            <span v-else class="text-muted">{{ t('common.never') }}</span>
          </template>
        </Column>

        <Column :header="t('integrations.whatsappDevices.actions')" :exportable="false">
          <template #body="{ data }">
            <div class="action-buttons">
              <Button
                v-if="data.status === 'disconnected'"
                icon="pi pi-qrcode"
                :label="t('integrations.whatsappDevices.connect')"
                severity="success"
                size="small"
                :disabled="loading"
                @click="connectDevice(data)"
              />
              <Button
                v-else-if="data.status === 'authenticated' || data.status === 'connected'"
                icon="pi pi-power-off"
                :label="t('integrations.whatsappDevices.disconnect')"
                severity="warning"
                size="small"
                :disabled="loading"
                @click="disconnectDevice(data)"
              />
              <Button
                icon="pi pi-trash"
                severity="danger"
                size="small"
                text
                :disabled="loading"
                @click="deleteDevice(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create Device Dialog -->
    <Dialog
      v-model:visible="showCreateDialog"
      :header="t('integrations.whatsappDevices.createDevice')"
      :modal="true"
      :style="{ width: '500px' }"
      class="create-dialog"
    >
      <div class="form-container">
        <div class="field">
          <label for="phone">{{ t('integrations.whatsappDevices.phoneNumber') }}</label>
          <div class="phone-input-group">
            <Dropdown
              v-model="selectedCountry"
              :options="countries"
              optionLabel="name"
              :disabled="loading"
              class="country-dropdown"
            >
              <template #value="{ value }">
                <span>{{ value.flag }} {{ value.dial }}</span>
              </template>
              <template #option="{ option }">
                <span>{{ option.flag }} {{ option.dial }} {{ option.name }}</span>
              </template>
            </Dropdown>
            <InputText
              id="phone"
              v-model="localPhone"
              placeholder="1112345678"
              :disabled="loading"
              class="phone-number-input"
            />
          </div>
          <small class="field-hint">{{ t('integrations.whatsappDevices.enterWithoutCode') }}</small>
        </div>

        <div class="field">
          <label for="name">{{ t('integrations.whatsappDevices.deviceNameLabel') }}</label>
          <InputText
            id="name"
            v-model="newDevice.device_name"
            :placeholder="t('integrations.whatsappDevices.deviceNamePlaceholder')"
            class="w-full"
            :disabled="loading"
          />
          <small class="field-hint">{{ t('integrations.whatsappDevices.deviceNameHint') }}</small>
        </div>
      </div>

      <template #footer>
        <Button
          :label="t('common.cancel')"
          icon="pi pi-times"
          text
          :disabled="loading"
          @click="showCreateDialog = false"
        />
        <Button
          :label="t('integrations.whatsappDevices.create')"
          icon="pi pi-check"
          :loading="loading"
          @click="createDevice"
        />
      </template>
    </Dialog>

    <!-- QR Code Dialog -->
    <Dialog
      v-model:visible="showQRDialog"
      :header="qrCode ? 'Escanear Código QR' : 'Generando Código QR…'"
      :modal="true"
      :style="{ width: '500px' }"
      :closable="true"
      class="qr-dialog"
      @hide="closeQRDialog"
    >
      <div class="qr-container">
        <!-- QR instructions -->
        <div v-if="qrCode" class="qr-instructions">
          <ol class="instructions-list">
            <li>Abre WhatsApp en tu teléfono</li>
            <li>Ve a Configuración &gt; Dispositivos vinculados</li>
            <li>Toca en "Vincular un dispositivo"</li>
            <li>Escanea este código QR</li>
          </ol>
        </div>

        <!-- QR image -->
        <div v-if="qrCode" class="qr-code-wrapper">
          <img
            :src="qrCode"
            alt="QR Code"
            class="qr-code"
            style="background: white; padding: 0.75rem; border-radius: 0.5rem; display: block"
          />
        </div>

        <!-- Loading state -->
        <div v-else class="qr-loading">
          <ProgressSpinner style="width: 2.5rem; height: 2.5rem" />
          <p class="qr-loading-text">Conectando con WhatsApp…</p>
        </div>

        <!-- Warning -->
        <div v-if="qrCode" class="qr-warning">
          <i class="pi pi-exclamation-triangle warning-icon"></i>
          <span
            >Este código QR expira en 60 segundos. Si expira, cierra esta ventana y vuelve a
            conectar.</span
          >
        </div>
      </div>

      <template #footer>
        <Button label="Cancelar" icon="pi pi-times" text @click="closeQRDialog" />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
/* ── Layout ─────────────────────────────────────────────── */
.devices-view {
  max-width: 1200px;
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
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: var(--do-blue);
  flex-shrink: 0;
}

.whatsapp-icon {
  color: #25d366;
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

/* ── Panel ───────────────────────────────────────────────── */
.panel {
  border: 1px solid var(--do-border-light);
  border-radius: 0.75rem;
  overflow: hidden;
  background: var(--do-bg);
}

/* ── States ──────────────────────────────────────────────── */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 4rem 2rem;
}

.loading-text {
  font-size: 0.875rem;
  color: var(--do-text-muted);
  margin: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 4rem 2rem;
  text-align: center;
}

.empty-icon {
  font-size: 2.5rem;
  color: var(--do-text-muted);
  opacity: 0.4;
  margin-bottom: 0.5rem;
}

.empty-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--do-text);
  margin: 0;
}

.empty-subtitle {
  font-size: 0.875rem;
  color: var(--do-text-muted);
  margin: 0;
  max-width: 36ch;
}

/* ── DataTable overrides ─────────────────────────────────── */
.devices-table :deep(.p-datatable) {
  background: var(--do-bg);
  color: var(--do-text);
  border: none;
}

.devices-table :deep(.p-datatable-thead > tr > th) {
  background: rgba(255, 255, 255, 0.03);
  color: var(--do-text-muted);
  border-color: var(--do-border-light);
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.75rem 1rem;
}

.devices-table :deep(.p-datatable-tbody > tr) {
  background: var(--do-bg);
  color: var(--do-text);
  transition: background 0.15s;
}

.devices-table :deep(.p-datatable-tbody > tr:hover) {
  background: rgba(255, 255, 255, 0.04);
}

.devices-table :deep(.p-datatable-tbody > tr.p-row-odd) {
  background: rgba(255, 255, 255, 0.02);
}

.devices-table :deep(.p-datatable-tbody > tr > td) {
  border-color: var(--do-border-light);
  padding: 0.75rem 1rem;
}

.devices-table :deep(.p-paginator) {
  background: rgba(255, 255, 255, 0.025);
  border-top: 1px solid var(--do-border-light);
  color: var(--do-text-muted);
}

/* ── Table cell helpers ──────────────────────────────────── */
.device-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  color: var(--do-text);
}

.device-name i {
  color: var(--color-primary);
  font-size: 0.9rem;
}

.phone-number {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--do-text);
}

.date {
  font-size: 0.875rem;
  color: var(--do-text-muted);
}

.text-muted {
  color: var(--do-text-muted);
  font-style: italic;
  font-size: 0.875rem;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

/* ── Dialog overrides ────────────────────────────────────── */
:deep(.create-dialog.p-dialog),
:deep(.qr-dialog.p-dialog) {
  background: var(--do-bg);
  border: 1px solid var(--do-border-light);
  border-radius: 0.875rem;
  overflow: hidden;
}

:deep(.create-dialog .p-dialog-header),
:deep(.qr-dialog .p-dialog-header) {
  background: rgba(255, 255, 255, 0.025);
  border-bottom: 1px solid var(--do-border-light);
  color: var(--do-text);
  padding: 1rem 1.25rem;
}

:deep(.create-dialog .p-dialog-content),
:deep(.qr-dialog .p-dialog-content) {
  background: var(--do-bg);
  color: var(--do-text);
  padding: 1.25rem;
}

:deep(.create-dialog .p-dialog-footer),
:deep(.qr-dialog .p-dialog-footer) {
  background: rgba(255, 255, 255, 0.025);
  border-top: 1px solid var(--do-border-light);
  padding: 0.875rem 1.25rem;
}

/* ── Create device form ──────────────────────────────────── */
.form-container {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.field label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--do-text);
}

.field-hint {
  font-size: 0.8rem;
  color: var(--do-text-muted);
  font-style: italic;
}

.w-full {
  width: 100%;
}

.phone-input-group {
  display: flex;
  gap: 0;
}

.country-dropdown {
  flex-shrink: 0;
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.country-dropdown :deep(.p-dropdown) {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.phone-number-input {
  flex: 1;
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
  border-left: 0;
}

/* ── QR dialog content ───────────────────────────────────── */
.qr-container {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.qr-instructions {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--do-border-light);
  border-radius: 0.5rem;
  padding: 0.875rem 1rem;
}

.instructions-list {
  margin: 0;
  padding-left: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.instructions-list li {
  font-size: 0.875rem;
  color: var(--do-text-muted);
}

.qr-code-wrapper {
  display: flex;
  justify-content: center;
  padding: 0;
  background: var(--do-bg);
  border-radius: 0.5rem;
}

.qr-code {
  max-width: 280px;
  height: auto;
}

.qr-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 2.5rem 1rem;
}

.qr-loading-text {
  margin: 0;
  font-size: 0.875rem;
  color: var(--do-text-muted);
}

.qr-warning {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  background: rgba(255, 193, 7, 0.08);
  border: 1px solid rgba(255, 193, 7, 0.25);
  border-radius: 0.5rem;
  padding: 0.75rem 0.875rem;
  font-size: 0.8rem;
  color: var(--do-text-muted);
}

.warning-icon {
  color: var(--color-warning);
  font-size: 0.9rem;
  flex-shrink: 0;
  margin-top: 0.05rem;
}

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 768px) {
  .devices-view {
    padding: 0.75rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .page-header :deep(button) {
    width: 100%;
  }

  .action-buttons {
    flex-direction: column;
    width: 100%;
  }

  .action-buttons :deep(button) {
    width: 100%;
  }
}
</style>
