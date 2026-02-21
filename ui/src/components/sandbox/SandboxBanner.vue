<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Message from 'primevue/message'
import InlineMessage from 'primevue/inlinemessage'
import Button from 'primevue/button'

const STORAGE_KEY = 'sandbox-banner-closed'
const isBannerVisible = ref(true)

onMounted(() => {
  const isClosed = localStorage.getItem(STORAGE_KEY)
  if (isClosed === 'true') {
    isBannerVisible.value = false
  }
})

const closeBanner = () => {
  isBannerVisible.value = false
  localStorage.setItem(STORAGE_KEY, 'true')
}
</script>

<template>
  <div v-if="isBannerVisible" class="sandbox-banner">
    <Message severity="warn" :closable="false" class="mb-3">
      <div class="flex align-items-center gap-3">
        <i class="pi pi-exclamation-triangle text-3xl"></i>
        <div class="flex-1">
          <h3 class="m-0 mb-2 text-xl font-bold">Entorno de Pruebas Sandbox</h3>
          <p class="m-0 mb-2">
            Estás en <strong>modo sandbox</strong>. Este es un entorno de pruebas seguro donde
            puedes experimentar con tu asistente de IA sin consumir iteraciones de API ni afectar
            los datos de producción.
          </p>
          <div class="flex flex-wrap gap-2 mt-2">
            <InlineMessage severity="success" class="p-1">
              <i class="pi pi-check-circle mr-1"></i>
              Pruebas
            </InlineMessage>
            <InlineMessage severity="info" class="p-1">
              <i class="pi pi-shield mr-1"></i>
              Entorno Aislado
            </InlineMessage>
            <InlineMessage severity="warn" class="p-1">
              <i class="pi pi-exclamation-circle mr-1"></i>
              Solo Datos de Prueba
            </InlineMessage>
          </div>
        </div>
        <Button
          icon="pi pi-times"
          @click="closeBanner"
          class="p-button-text p-button-rounded close-button"
          v-tooltip.left="'Cerrar banner'"
        />
      </div>
    </Message>
  </div>
</template>

<style scoped>
.sandbox-banner {
  width: 100%;
}

:deep(.p-message-warn) {
  background: linear-gradient(
    135deg,
    var(--vt-c-warning-light) 0%,
    var(--vt-c-warning-lighter) 100%
  );
  border: none;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.15);
}

:deep(.p-message-warn .p-message-icon) {
  color: var(--vt-c-warning-dark);
}

:deep(.p-message-warn .p-message-text) {
  color: var(--vt-c-gray-800);
}

:deep(.p-inline-message) {
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
}

.text-xl {
  font-size: 1.25rem;
}

.text-3xl {
  font-size: 1.875rem;
}

.close-button {
  align-self: flex-start;
  color: var(--vt-c-warning-dark);
}

.close-button:hover {
  background-color: rgba(245, 158, 11, 0.1);
}
</style>
