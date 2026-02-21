<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'

const emit = defineEmits<{
  (e: 'code', authCode: string): void
}>()

const googleClient = ref<{
  requestCode: () => void
} | null>(null)

const buttonRef = ref<HTMLButtonElement | null>(null)
const showText = ref(true)
const buttonText = ref('Iniciar con Google')
const displayedText = ref(buttonText.value)

onMounted(() => {
  const google = window.google

  if (google?.accounts?.oauth2) {
    googleClient.value = google.accounts.oauth2.initCodeClient({
      client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
      scope: 'openid email profile',
      ux_mode: 'popup',
      callback: (response) => {
        emit('code', response.code)
      },
    })
  }
})

const loginWithGoogle = () => {
  googleClient.value?.requestCode()
}
</script>

<template>
  <Button
    ref="buttonRef"
    icon="pi pi-google"
    class="w-full max-w-[17.35rem] mx-auto google-button px-2 py-2"
    severity="secondary"
    @click="loginWithGoogle"
    :label="showText ? displayedText : ''"
  />
</template>

<style scoped>
/* Google Button - using PrimeVue classes */
.google-button {
  background-color: var(--color-primary);
  color: #ffffff;
  border: none;
  width: 3rem;
  overflow: hidden;
  transition: width 0.2s ease-in-out;
}

.google-button:hover {
  background-color: var(--color-primary-dark) !important;
  border: none !important;
}
</style>
