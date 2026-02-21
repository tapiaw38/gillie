<script setup lang="ts">
import { watch } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import type { RequestResetPasswordParams } from '@/types/auth.ts'
import { useAuth } from '@/composables/useAuth'
import { useErrorToast } from '@/composables/useErrorToast'
import { useForm, useField } from 'vee-validate'
import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'

const emit = defineEmits<{
  backToLogin: []
}>()

const toast = useToast()
const {
  requestResetPassword,
  requestResetPasswordError,
  isRequestResetPasswordError,
  isRequestResetPasswordPending,
  isRequestResetPasswordSuccess,
} = useAuth()

const errorWatchers = [
  {
    flag: isRequestResetPasswordError,
    summary: 'Error al solicitar recuperación',
    detail: requestResetPasswordError,
  },
]

useErrorToast(errorWatchers)

watch(isRequestResetPasswordSuccess, (value) => {
  if (value) {
    toast.add({
      severity: 'success',
      summary: 'Email enviado',
      detail: 'Se ha enviado un enlace de recuperación a tu correo electrónico',
      life: 5000,
    })
  }
})

const schema = z.object({
  email: z.string().email('Email inválido'),
})

const { handleSubmit, errors } = useForm({
  validationSchema: toTypedSchema(schema),
})

const { value: email } = useField<string>('email')

const onSubmit = handleSubmit(async (values) => {
  const params: RequestResetPasswordParams = {
    email: values.email,
  }
  try {
    await requestResetPassword(params)
  } catch (error) {
    console.error('Error al solicitar recuperación de contraseña:', error)
  }
})

const goBackToLogin = () => {
  emit('backToLogin')
}
</script>

<template>
  <form @submit.prevent="onSubmit">
    <div class="flex flex-column gap-2">
      <p class="text-muted mb-3">
        Ingresa tu correo electrónico y te enviaremos un enlace para restablecer tu contraseña.
      </p>
      <div class="flex flex-column gap-1">
        <label for="email">Email</label>
        <InputText id="email" type="text" v-model="email" class="w-full" />
        <small class="text-danger">{{ errors.email }}</small>
      </div>
    </div>

    <div class="flex flex-column gap-2 mt-4">
      <Button
        label="Enviar enlace de recuperación"
        icon="pi pi-send"
        class="w-full"
        type="submit"
        :disabled="isRequestResetPasswordPending"
      />

      <Button
        label="Volver al inicio de sesión"
        icon="pi pi-arrow-left"
        text
        severity="secondary"
        class="w-full"
        @click="goBackToLogin"
      />
    </div>

    <div v-if="isRequestResetPasswordSuccess" class="success-message mt-3">
      <i class="pi pi-check-circle"></i>
      <span
        >Revisa tu correo electrónico para continuar con el restablecimiento de contraseña.</span
      >
    </div>
  </form>

  <!-- Toast for Notifications -->
  <Toast position="top-right" />
</template>

<style scoped>
.text-muted {
  color: var(--vt-c-gray-500);
  font-size: 0.875rem;
  line-height: 1.5;
  margin: 0;
}

.success-message {
  padding: 1rem;
  background: var(--surface-100);
  border: 1px solid var(--success-color);
  border-radius: 0.5rem;
  color: var(--success-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.success-message i {
  font-size: 1.125rem;
}
</style>
