<script setup lang="ts">
import { watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Button from 'primevue/button'
import Toast from 'primevue/toast'
import Password from 'primevue/password'
import { useToast } from 'primevue/usetoast'
import type { ResetPasswordParams } from '@/types/auth.ts'
import { useAuth } from '@/composables/useAuth'
import { useErrorToast } from '@/composables/useErrorToast'
import { useForm, useField } from 'vee-validate'
import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const {
  resetPassword,
  resetPasswordError,
  isResetPasswordError,
  isResetPasswordPending,
  isResetPasswordSuccess,
} = useAuth()

const errorWatchers = [
  {
    flag: isResetPasswordError,
    summary: 'Error al restablecer contraseña',
    detail: resetPasswordError,
  },
]

useErrorToast(errorWatchers)

watch(isResetPasswordSuccess, (value) => {
  if (value) {
    toast.add({
      severity: 'success',
      summary: 'Contraseña restablecida',
      detail:
        'Tu contraseña ha sido actualizada correctamente. Serás redirigido al inicio de sesión.',
      life: 3000,
    })

    setTimeout(() => {
      router.push('/auth')
    }, 3000)
  }
})

const token = computed(() => route.query.token as string)

const schema = z
  .object({
    password: z
      .string()
      .min(8, 'La contraseña debe tener al menos 8 caracteres')
      .regex(/[A-Z]/, 'Debe contener al menos una letra mayúscula')
      .regex(/[a-z]/, 'Debe contener al menos una letra minúscula')
      .regex(/[0-9]/, 'Debe contener al menos un número')
      .regex(/[^A-Za-z0-9]/, 'Debe contener al menos un carácter especial'),
    confirmPassword: z.string().min(1, 'Confirma tu contraseña'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Las contraseñas no coinciden',
    path: ['confirmPassword'],
  })

const { handleSubmit, errors } = useForm({
  validationSchema: toTypedSchema(schema),
})

const { value: password } = useField<string>('password')
const { value: confirmPassword } = useField<string>('confirmPassword')

const onSubmit = handleSubmit(async (values) => {
  if (!token.value) {
    toast.add({
      severity: 'error',
      summary: 'Token inválido',
      detail: 'No se encontró un token válido en la URL',
      life: 5000,
    })
    return
  }

  const params: ResetPasswordParams = {
    token: token.value,
    password: values.password,
  }

  try {
    await resetPassword(params)
  } catch (error) {
    console.error('Error al restablecer contraseña:', error)
  }
})
</script>

<template>
  <div class="reset-password-container">
    <div class="reset-password-header">
      <div class="icon-container">
        <i class="pi pi-lock"></i>
      </div>
      <h2>Restablecer Contraseña</h2>
      <p class="subtitle">Ingresa tu nueva contraseña</p>
    </div>

    <form @submit.prevent="onSubmit">
      <div class="flex flex-column gap-3">
        <div class="flex flex-column gap-1">
          <label for="password">Nueva Contraseña</label>
          <Password
            id="password"
            v-model="password"
            toggleMask
            :feedback="true"
            class="w-full"
            inputClass="w-full"
          >
            <template #header>
              <h6>Elige una contraseña</h6>
            </template>
            <template #footer>
              <p class="mt-2">Requisitos:</p>
              <ul class="pl-2 ml-2 mt-0" style="line-height: 1.5">
                <li>Mínimo 8 caracteres</li>
                <li>Una letra mayúscula</li>
                <li>Una letra minúscula</li>
                <li>Un número</li>
                <li>Un carácter especial</li>
              </ul>
            </template>
          </Password>
          <small class="text-danger">{{ errors.password }}</small>
        </div>

        <div class="flex flex-column gap-1">
          <label for="confirmPassword">Confirmar Contraseña</label>
          <Password
            id="confirmPassword"
            v-model="confirmPassword"
            :feedback="false"
            toggleMask
            class="w-full"
            inputClass="w-full"
          />
          <small class="text-danger">{{ errors.confirmPassword }}</small>
        </div>
      </div>

      <div class="flex flex-column gap-2 mt-4">
        <Button
          label="Restablecer Contraseña"
          icon="pi pi-check"
          class="w-full"
          type="submit"
          :disabled="isResetPasswordPending || !token"
        />

        <Button
          label="Volver al inicio de sesión"
          icon="pi pi-arrow-left"
          text
          severity="secondary"
          class="w-full"
          @click="router.push('/auth')"
        />
      </div>

      <div v-if="!token" class="error-message mt-3">
        <i class="pi pi-exclamation-triangle"></i>
        <span
          >Token inválido o no proporcionado. Por favor, solicita un nuevo enlace de
          recuperación.</span
        >
      </div>
    </form>

    <!-- Toast for Notifications -->
    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.reset-password-container {
  width: 100%;
}

.reset-password-header {
  text-align: center;
  margin-bottom: 2rem;
}

.icon-container {
  width: 4rem;
  height: 4rem;
  background: var(--gradient-primary);
  border-radius: 1rem;
  margin: 0 auto 1rem auto;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 32px var(--gradient-primary-shadow);
}

.icon-container i {
  font-size: 2rem;
  color: var(--vt-c-white);
}

.reset-password-header h2 {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--vt-c-gray-800);
  margin: 0 0 0.5rem 0;
}

.subtitle {
  color: var(--vt-c-gray-500);
  font-size: 0.875rem;
  margin: 0;
}

.error-message {
  padding: 1rem;
  background: var(--surface-100);
  border: 1px solid var(--error-color);
  border-radius: 0.5rem;
  color: var(--error-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.error-message i {
  font-size: 1.125rem;
}

:deep(.p-password-input) {
  width: 100%;
}
</style>
