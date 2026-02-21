<script setup lang="ts">
import { useRouter } from 'vue-router'
import { watch, ref, onMounted } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Toast from 'primevue/toast'
import type { LoginParams } from '@/types/auth.ts'
import { useAuth } from '@/composables/useAuth'
import { useErrorToast } from '@/composables/useErrorToast'
import { useForm, useField } from 'vee-validate'
import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'

const emit = defineEmits<{
  showForgotPassword: []
}>()

const router = useRouter()
const { loginUser, loginError, isLoginError, isLoginPending, isLoginSuccess, meUser, user } =
  useAuth()

const failedAttempts = ref(0)
const FAILED_ATTEMPTS_THRESHOLD = 3
const STORAGE_KEY = 'login_failed_attempts'

onMounted(() => {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    failedAttempts.value = parseInt(stored, 10)
  }
})

const errorWatchers = [
  {
    flag: isLoginError,
    summary: 'Error al iniciar sesión',
    detail: loginError,
  },
]

const { toast } = useErrorToast(errorWatchers)

watch(isLoginSuccess, (value) => {
  if (value) {
    failedAttempts.value = 0
    localStorage.removeItem(STORAGE_KEY)

    toast.add({
      severity: 'success',
      summary: 'Inicio de sesión exitoso',
      detail: 'Bienvenido de vuelta',
      life: 3000,
    })
  }
})

watch(isLoginError, (value) => {
  if (value) {
    failedAttempts.value++
    localStorage.setItem(STORAGE_KEY, failedAttempts.value.toString())
  }
})

const schema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'Contraseña requerida'),
})

const { handleSubmit, errors } = useForm({
  validationSchema: toTypedSchema(schema),
})

const { value: email } = useField<string>('email')
const { value: password } = useField<string>('password')

const onSubmit = handleSubmit(async (values) => {
  const loginParams: LoginParams = {
    email: values.email,
    password: values.password,
  }
  try {
    await loginUser(loginParams)
    await new Promise((resolve) => setTimeout(resolve, 100))
    if (isLoginSuccess.value) {
      if (!user.value) {
        await meUser()
      }
      await router.push('/dashboard')
    }
  } catch (error) {
    console.error('Error al iniciar sesión:', error)
  }
})

const showForgotPasswordForm = () => {
  emit('showForgotPassword')
}
</script>

<template>
  <form @submit.prevent="onSubmit">
    <div class="flex flex-column gap-2">
      <div class="flex flex-column gap-1">
        <label for="email">Email</label>
        <InputText id="email" type="text" v-model="email" class="w-full" />
        <small class="text-danger">{{ errors.email }}</small>
      </div>
      <div class="flex flex-column gap-1">
        <label for="password">Password</label>
        <InputText id="password" type="password" v-model="password" class="w-full" />
        <small class="text-danger">{{ errors.password }}</small>
      </div>
    </div>

    <!-- Show "Forgot Password?" link after 3 failed attempts -->
    <div v-if="failedAttempts >= FAILED_ATTEMPTS_THRESHOLD" class="mt-2">
      <Button
        label="¿Olvidaste tu contraseña?"
        text
        severity="secondary"
        class="p-button-link forgot-password-link"
        @click="showForgotPasswordForm"
      />
    </div>

    <div class="flex mt-4">
      <Button
        label="Iniciar Sesión"
        icon=""
        class="w-full"
        type="submit"
        :disabled="isLoginPending"
      />
    </div>
  </form>

  <p class="text-danger" v-if="isLoginError">Error: {{ loginError?.message }}</p>

  <!-- Toast for Notifications -->
  <Toast position="top-right" />
</template>

<style scoped>
.forgot-password-link {
  padding: 0;
  font-size: 0.875rem;
  color: var(--primary-color);
}

.forgot-password-link:hover {
  text-decoration: underline;
}
</style>
