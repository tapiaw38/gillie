<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useWhatsApp } from '@/composables/useWhatsApp'
import { useToast } from 'primevue/usetoast'
import type { WhatsAppDevice, CreateDeviceRequest } from '@/services/whatsapp'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'

const whatsapp = useWhatsApp()
const toast = useToast()

// State
const devices = ref<WhatsAppDevice[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const showQRDialog = ref(false)
const qrCode = ref<string>()
const selectedDevice = ref<WhatsAppDevice>()

// Form data
const newDevice = ref<CreateDeviceRequest>({
  phone_number: '',
  device_name: '',
})

// Computed
const hasDevices = computed(() => devices.value?.length > 0)

// Methods
const loadDevices = async () => {
  loading.value = true
  try {
    devices.value = await whatsapp.listDevices()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudieron cargar los dispositivos',
      life: 3000,
    })
    console.error('Error loading devices:', error)
  } finally {
    loading.value = false
  }
}

const createDevice = async () => {
  if (!newDevice.value.phone_number || !newDevice.value.device_name) {
    toast.add({
      severity: 'warn',
      summary: 'Campos requeridos',
      detail: 'Por favor completa todos los campos',
      life: 3000,
    })
    return
  }

  loading.value = true
  try {
    const device = await whatsapp.createDevice(newDevice.value)
    toast.add({
      severity: 'success',
      summary: 'Dispositivo creado',
      detail: `Dispositivo ${device.device_name} creado exitosamente`,
      life: 3000,
    })
    showCreateDialog.value = false
    newDevice.value = { phone_number: '', device_name: '' }
    await loadDevices()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo crear el dispositivo',
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
    const authenticatedDevice = await whatsapp.authenticateDevice(device.id, {
      auth_method: 'qr',
    })
    qrCode.value = authenticatedDevice.qr_code
    selectedDevice.value = device
    showQRDialog.value = true

    toast.add({
      severity: 'info',
      summary: 'Código QR generado',
      detail: 'Escanea el código QR con WhatsApp',
      life: 5000,
    })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo generar el código QR',
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
      summary: 'Dispositivo desconectado',
      detail: `${device.device_name} desconectado exitosamente`,
      life: 3000,
    })
    await loadDevices()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo desconectar el dispositivo',
      life: 3000,
    })
    console.error('Error disconnecting device:', error)
  } finally {
    loading.value = false
  }
}

const deleteDevice = async (device: WhatsAppDevice) => {
  if (!confirm(`¿Estás seguro de eliminar el dispositivo ${device.device_name}?`)) {
    return
  }

  loading.value = true
  try {
    await whatsapp.deleteDevice(device.id)
    toast.add({
      severity: 'success',
      summary: 'Dispositivo eliminado',
      detail: `${device.device_name} eliminado exitosamente`,
      life: 3000,
    })
    await loadDevices()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo eliminar el dispositivo',
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
    authenticated: 'Autenticado',
    connected: 'Conectado',
    connecting: 'Conectando',
    disconnected: 'Desconectado',
  }
  return labelMap[status] || status
}

const openCreateDialog = () => {
  newDevice.value = { phone_number: '', device_name: '' }
  showCreateDialog.value = true
}

const closeQRDialog = async () => {
  showQRDialog.value = false
  qrCode.value = undefined

  if (selectedDevice.value) {
    const deviceToConnect = selectedDevice.value
    selectedDevice.value = undefined

    setTimeout(async () => {
      try {
        loading.value = true
        await whatsapp.connectDevice(deviceToConnect.id, 'qr')
        toast.add({
          severity: 'success',
          summary: 'Dispositivo conectado',
          detail: 'El dispositivo se conectó exitosamente',
          life: 3000,
        })
      } catch (error) {
        console.log('Auto-connect attempt:', error)
      } finally {
        loading.value = false
        await loadDevices()
      }
    }, 2000)
  } else {
    await loadDevices()
  }
}

onMounted(() => {
  loadDevices()
})
</script>

<template>
  <div class="whatsapp-devices-view">
    <Toast />

    <div class="header-section">
      <div class="header-content">
        <h1 class="title">
          <i class="pi pi-whatsapp"></i>
          Dispositivos WhatsApp
        </h1>
        <p class="subtitle">Gestiona tus dispositivos WhatsApp conectados al asistente IA</p>
      </div>
      <Button
        label="Agregar Dispositivo"
        icon="pi pi-plus"
        @click="openCreateDialog"
        :disabled="loading"
      />
    </div>

    <Card class="devices-card">
      <template #content>
        <Message v-if="!hasDevices && !loading" severity="info" :closable="false">
          No tienes dispositivos WhatsApp configurados. Haz clic en "Agregar Dispositivo" para
          comenzar.
        </Message>

        <div v-if="loading && !hasDevices" class="loading-container">
          <ProgressSpinner />
        </div>

        <DataTable
          v-if="hasDevices"
          :value="devices"
          :loading="loading"
          stripedRows
          responsiveLayout="scroll"
          :paginator="devices.length > 10"
          :rows="10"
        >
          <Column field="device_name" header="Nombre del Dispositivo" :sortable="true">
            <template #body="{ data }">
              <div class="device-name">
                <i class="pi pi-mobile"></i>
                <span>{{ data.device_name }}</span>
              </div>
            </template>
          </Column>

          <Column field="phone_number" header="Teléfono" :sortable="true">
            <template #body="{ data }">
              <span class="phone-number">{{ data.phone_number }}</span>
            </template>
          </Column>

          <Column field="status" header="Estado" :sortable="true">
            <template #body="{ data }">
              <Tag
                :severity="getStatusSeverity(data.status)"
                :value="getStatusLabel(data.status)"
              />
            </template>
          </Column>

          <Column field="last_connected_at" header="Última Conexión" :sortable="true">
            <template #body="{ data }">
              <span v-if="data.last_connected_at" class="date">
                {{ new Date(data.last_connected_at).toLocaleString('es-ES') }}
              </span>
              <span v-else class="text-muted">Nunca</span>
            </template>
          </Column>

          <Column header="Acciones" :exportable="false">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  v-if="data.status === 'disconnected'"
                  icon="pi pi-qrcode"
                  label="Conectar"
                  severity="success"
                  size="small"
                  @click="connectDevice(data)"
                  :disabled="loading"
                />
                <Button
                  v-else-if="data.status === 'authenticated' || data.status === 'connected'"
                  icon="pi pi-power-off"
                  label="Desconectar"
                  severity="warning"
                  size="small"
                  @click="disconnectDevice(data)"
                  :disabled="loading"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  size="small"
                  text
                  @click="deleteDevice(data)"
                  :disabled="loading"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Create Device Dialog -->
    <Dialog
      v-model:visible="showCreateDialog"
      header="Agregar Nuevo Dispositivo"
      :modal="true"
      :style="{ width: '500px' }"
    >
      <div class="form-container">
        <div class="field">
          <label for="phone">Número de Teléfono</label>
          <InputText
            id="phone"
            v-model="newDevice.phone_number"
            placeholder="+1234567890"
            class="w-full"
            :disabled="loading"
          />
          <small class="text-muted">Incluye el código de país (ej: +52, +1, +34)</small>
        </div>

        <div class="field">
          <label for="name">Nombre del Dispositivo</label>
          <InputText
            id="name"
            v-model="newDevice.device_name"
            placeholder="Mi Teléfono"
            class="w-full"
            :disabled="loading"
          />
          <small class="text-muted">Un nombre descriptivo para identificar tu dispositivo</small>
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          icon="pi pi-times"
          text
          @click="showCreateDialog = false"
          :disabled="loading"
        />
        <Button label="Crear" icon="pi pi-check" @click="createDevice" :loading="loading" />
      </template>
    </Dialog>

    <!-- QR Code Dialog -->
    <Dialog
      v-model:visible="showQRDialog"
      header="Escanear Código QR"
      :modal="true"
      :style="{ width: '500px' }"
      @hide="closeQRDialog"
    >
      <div class="qr-container">
        <Message severity="info" :closable="false" class="qr-instructions">
          <ol>
            <li>Abre WhatsApp en tu teléfono</li>
            <li>Ve a Configuración > Dispositivos vinculados</li>
            <li>Toca en "Vincular un dispositivo"</li>
            <li>Escanea este código QR</li>
          </ol>
        </Message>

        <div v-if="qrCode" class="qr-code-wrapper">
          <img :src="qrCode" alt="QR Code" class="qr-code" />
        </div>
        <div v-else class="loading-container">
          <ProgressSpinner />
        </div>

        <Message severity="warn" :closable="false" class="qr-warning">
          Este código QR expira en 60 segundos. Si expira, cierra esta ventana y vuelve a conectar.
        </Message>
      </div>

      <template #footer>
        <Button label="Cerrar" icon="pi pi-times" @click="closeQRDialog" />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.whatsapp-devices-view {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.header-content {
  .title {
    font-size: 2rem;
    font-weight: 700;
    color: var(--vt-c-gray-700);
    margin: 0 0 0.5rem 0;
    display: flex;
    align-items: center;
    gap: 0.75rem;

    i {
      color: #25d366;
      font-size: 2rem;
    }
  }

  .subtitle {
    color: var(--vt-c-gray-700);
    margin: 0;
    font-size: 1rem;
  }
}

.devices-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 3rem;
}

.device-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;

  i {
    color: var(--primary-color);
  }
}

.phone-number {
  font-family: 'Courier New', monospace;
  font-weight: 600;
}

.date {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.text-muted {
  color: var(--text-color-secondary);
  font-style: italic;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem 0;

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;

    label {
      font-weight: 600;
      color: var(--text-color);
    }

    small {
      font-size: 0.875rem;
      color: var(--text-color-secondary);
    }
  }
}

.qr-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem 0;
}

.qr-instructions {
  ol {
    margin: 0;
    padding-left: 1.5rem;

    li {
      margin: 0.5rem 0;
    }
  }
}

.qr-code-wrapper {
  display: flex;
  justify-content: center;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  border: 2px solid var(--surface-border);
}

.qr-code {
  max-width: 100%;
  height: auto;
  display: block;
}

.qr-warning {
  font-size: 0.875rem;
}

@media (max-width: 768px) {
  .whatsapp-devices-view {
    padding: 1rem;
  }

  .header-section {
    flex-direction: column;
    align-items: stretch;

    button {
      width: 100%;
    }
  }

  .action-buttons {
    flex-direction: column;
    width: 100%;

    button {
      width: 100%;
    }
  }
}
</style>
