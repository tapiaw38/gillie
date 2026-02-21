<script setup lang="ts">
import { useRouter } from 'vue-router'
import { watchEffect, watch } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Toast from 'primevue/toast'
import { useForm, useField } from 'vee-validate'
import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'
import type { RegisterParams } from '@/types/auth.ts'
import { useAuth } from '@/composables/useAuth'
import { useErrorToast } from '@/composables/useErrorToast'
import LoadingSpinner from '../LoadingSpinner/LoadingSpinner.vue'

const router = useRouter()
const { registerUser, registerError, isRegisterError, isRegisterPending, isRegisterSuccess } =
  useAuth()

const errorWatchers = [
  {
    flag: isRegisterError,
    summary: 'Error al crear cuenta',
    detail: registerError,
  },
]

const { toast } = useErrorToast(errorWatchers)

watch(isRegisterSuccess, (value) => {
  if (value) {
    toast.add({
      severity: 'success',
      summary: 'Cuenta creada exitosamente',
      detail: 'Tu cuenta ha sido creada. Ahora puedes iniciar sesión.',
      life: 4000,
    })
  }
})

const schema = z
  .object({
    first_name: z.string().min(1, 'Nombre requerido'),
    last_name: z.string().min(1, 'Apellido requerido'),
    email: z.string().email('Email inválido'),
    password: z.string().min(6, 'Contraseña muy corta'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    path: ['confirmPassword'],
    message: 'Las contraseñas no coinciden',
  })

const { handleSubmit, errors } = useForm({
  validationSchema: toTypedSchema(schema),
})

const { value: first_name } = useField<string>('first_name')
const { value: last_name } = useField<string>('last_name')
const { value: email } = useField<string>('email')
const { value: password } = useField<string>('password')
const { value: confirmPassword } = useField<string>('confirmPassword')

const onSubmit = handleSubmit(async (values) => {
  const registerParams: RegisterParams = {
    first_name: values.first_name,
    last_name: values.last_name,
    email: values.email,
    password: values.password,
  }

  try {
    await registerUser(registerParams)
  } catch (error) {
    console.error('Error en registro:', error)
  }
})

watchEffect(() => {
  if (isRegisterSuccess.value) {
    router.push('/auth')
  }
})
</script>

<template>
  <form @submit.prevent="onSubmit">
    <div class="flex flex-column gap-2">
      <div class="grid">
        <div class="col-12 md:col-6">
          <div class="flex flex-column gap-1">
            <label for="first_name">Nombre</label>
            <InputText id="first_name" type="text" v-model="first_name" class="w-full" />
            <small class="text-danger">{{ errors.first_name }}</small>
          </div>
        </div>

        <div class="col-12 md:col-6">
          <div class="flex flex-column gap-1">
            <label for="last_name">Apellido</label>
            <InputText id="last_name" type="text" v-model="last_name" class="w-full" />
            <small class="text-danger">{{ errors.last_name }}</small>
          </div>
        </div>
      </div>

      <div class="flex flex-column gap-1">
        <label for="email">Email</label>
        <InputText id="email" type="email" v-model="email" class="w-full" />
        <small class="text-danger">{{ errors.email }}</small>
      </div>

      <div class="grid">
        <div class="col-12 md:col-6">
          <div class="flex flex-column gap-1">
            <label for="password">Contraseña</label>
            <InputText id="password" type="password" v-model="password" class="w-full" />
            <small class="text-danger">{{ errors.password }}</small>
          </div>
        </div>

        <div class="col-12 md:col-6">
          <div class="flex flex-column gap-1">
            <label for="confirmPassword">Confirmar Contraseña</label>
            <InputText id="confirmPassword" type="password" v-model="confirmPassword" class="w-full" />
            <small class="text-danger">{{ errors.confirmPassword }}</small>
          </div>
        </div>
      </div>
    </div>

    <div class="flex mt-4">
      <Button type="submit" label="Crear Cuenta" class="w-full" />
    </div>
  </form>

  <div v-if="isRegisterPending" class="flex justify-center items-center">
    <LoadingSpinner />
  </div>

  <div v-if="isRegisterError" class="flex justify-center items-center">
    <p class="text-danger">{{ registerError }}</p>
  </div>

  <!-- Toast for Notifications -->
  <Toast position="top-right" />
</template>

<style scoped></style>
