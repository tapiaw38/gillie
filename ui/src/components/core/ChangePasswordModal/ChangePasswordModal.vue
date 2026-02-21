<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import DefaultModal from '@/components/core/shared/DefaultModal/DefaultModal.vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import Message from 'primevue/message'
import { useAuth } from '@/composables/useAuth'
import { useForm, useField } from 'vee-validate'
import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'

export interface ChangePasswordModalProps {
  isVisible: boolean
}

const props = defineProps<ChangePasswordModalProps>()
const emit = defineEmits(['update:visible', 'success'])

const {
  changePassword,
  isChangePasswordPending,
  isChangePasswordSuccess,
  isChangePasswordError,
  changePasswordError,
} = useAuth()

const showOldPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)

// Zod schema for password validation
const passwordRegex = {
  uppercase: /[A-Z]/,
  lowercase: /[a-z]/,
  number: /\d/,
  special: /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/,
}

const schema = z
  .object({
    oldPassword: z.string().min(1, 'La contraseña actual es requerida'),
    newPassword: z
      .string()
      .min(8, 'La contraseña debe tener mínimo 8 caracteres')
      .regex(passwordRegex.uppercase, 'La contraseña debe contener: una letra mayúscula')
      .regex(passwordRegex.lowercase, 'La contraseña debe contener: una letra minúscula')
      .regex(passwordRegex.number, 'La contraseña debe contener: un número')
      .regex(
        passwordRegex.special,
        'La contraseña debe contener: un carácter especial (!@#$%^&*()_+-=[]{} etc.)',
      ),
    confirmPassword: z.string().min(1, 'Debes confirmar la nueva contraseña'),
  })
  .refine((data) => data.newPassword !== data.oldPassword, {
    path: ['newPassword'],
    message: 'La nueva contraseña debe ser diferente a la actual',
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    path: ['confirmPassword'],
    message: 'Las contraseñas no coinciden',
  })

const { handleSubmit, errors, resetForm } = useForm({
  validationSchema: toTypedSchema(schema),
  initialValues: {
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  },
})

const { value: oldPassword } = useField<string>('oldPassword')
const { value: newPassword } = useField<string>('newPassword')
const { value: confirmPassword } = useField<string>('confirmPassword')

const passwordStrength = computed(() => {
  if (!newPassword.value) return { level: 0, label: '', color: 'danger' }

  let strength = 0
  const password = newPassword.value

  // Length check
  if (password.length >= 8) strength += 20
  if (password.length >= 12) strength += 10

  // Uppercase check
  if (passwordRegex.uppercase.test(password)) strength += 20

  // Lowercase check
  if (passwordRegex.lowercase.test(password)) strength += 20

  // Number check
  if (passwordRegex.number.test(password)) strength += 15

  // Special character check
  if (passwordRegex.special.test(password)) strength += 15

  let label = ''
  let color = 'danger'

  if (strength < 40) {
    label = 'Muy débil'
    color = 'danger'
  } else if (strength < 60) {
    label = 'Débil'
    color = 'warning'
  } else if (strength < 80) {
    label = 'Media'
    color = 'info'
  } else {
    label = 'Fuerte'
    color = 'success'
  }

  return { level: strength, label, color }
})

const isFormValid = computed(() => {
  return (
    oldPassword.value &&
    newPassword.value &&
    confirmPassword.value &&
    !errors.value.oldPassword &&
    !errors.value.newPassword &&
    !errors.value.confirmPassword &&
    newPassword.value === confirmPassword.value &&
    newPassword.value !== oldPassword.value &&
    passwordStrength.value.level >= 60
  )
})

watch(isChangePasswordSuccess, (value) => {
  if (value) {
    resetForm()
    emit('success')
    emit('update:visible', false)
  }
})

watch(
  () => props.isVisible,
  (newValue) => {
    if (!newValue) {
      resetForm()
      showOldPassword.value = false
      showNewPassword.value = false
      showConfirmPassword.value = false
    }
  },
)

const handleClose = (value: boolean) => {
  if (!value) {
    resetForm()
  }
  emit('update:visible', value)
}

const onSubmit = handleSubmit(async (values) => {
  try {
    await changePassword({
      old_password: values.oldPassword,
      new_password: values.newPassword,
    })
  } catch (error) {
    console.error('Error changing password:', error)
  }
})

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const getErrorMessage = (error: any): string => {
  if (!error) return 'Error desconocido'

  if (typeof error === 'string') return error

  if (error instanceof Error) return error.message

  if (error.response?.data?.message) return error.response.data.message

  if (error.response?.data?.detail) return error.response.data.detail

  return 'Error al cambiar la contraseña'
}
</script>

<template>
  <DefaultModal
    :isVisible="props.isVisible"
    @update:visible="handleClose"
    title="Cambiar Contraseña"
    width="35rem"
  >
    <form @submit.prevent="onSubmit" class="change-password-form">
      <!-- Error Message -->
      <Message
        v-if="isChangePasswordError"
        severity="error"
        :closable="false"
        class="error-message"
      >
        {{ getErrorMessage(changePasswordError) }}
      </Message>

      <!-- Old Password Field -->
      <div class="form-field">
        <label for="old_password" class="form-label">
          Contraseña Actual <span class="required">*</span>
        </label>
        <div class="password-input-wrapper">
          <InputText
            id="old_password"
            v-model="oldPassword"
            :type="showOldPassword ? 'text' : 'password'"
            placeholder="Ingresa tu contraseña actual"
            :class="{ 'p-invalid': errors.oldPassword }"
            autocomplete="current-password"
            class="password-input"
          />
          <Button
            :icon="showOldPassword ? 'pi pi-eye-slash' : 'pi pi-eye'"
            severity="secondary"
            text
            type="button"
            @click="showOldPassword = !showOldPassword"
            class="toggle-password-btn"
            tabindex="-1"
          />
        </div>
        <small v-if="errors.oldPassword" class="error-text">
          {{ errors.oldPassword }}
        </small>
      </div>

      <!-- New Password Field -->
      <div class="form-field">
        <label for="new_password" class="form-label">
          Nueva Contraseña <span class="required">*</span>
        </label>
        <div class="password-input-wrapper">
          <InputText
            id="new_password"
            v-model="newPassword"
            :type="showNewPassword ? 'text' : 'password'"
            placeholder="Ingresa tu nueva contraseña"
            :class="{ 'p-invalid': errors.newPassword }"
            autocomplete="new-password"
            class="password-input"
          />
          <Button
            :icon="showNewPassword ? 'pi pi-eye-slash' : 'pi pi-eye'"
            severity="secondary"
            text
            type="button"
            @click="showNewPassword = !showNewPassword"
            class="toggle-password-btn"
            tabindex="-1"
          />
        </div>

        <!-- Password Strength Indicator -->
        <div v-if="newPassword" class="password-strength">
          <div class="strength-header">
            <span class="strength-label">Fortaleza:</span>
            <span :class="['strength-value', `strength-${passwordStrength.color}`]">
              {{ passwordStrength.label }}
            </span>
          </div>
          <ProgressBar
            :value="passwordStrength.level"
            :showValue="false"
            :class="`strength-bar-${passwordStrength.color}`"
          />
        </div>

        <small v-if="errors.newPassword" class="error-text">
          {{ errors.newPassword }}
        </small>

        <!-- Password Requirements -->
        <div class="password-requirements">
          <p class="requirements-title">La contraseña debe contener:</p>
          <ul class="requirements-list">
            <li :class="{ valid: newPassword.length >= 8 }">
              <i :class="newPassword.length >= 8 ? 'pi pi-check' : 'pi pi-times'"></i>
              Mínimo 8 caracteres
            </li>
            <li :class="{ valid: passwordRegex.uppercase.test(newPassword) }">
              <i
                :class="passwordRegex.uppercase.test(newPassword) ? 'pi pi-check' : 'pi pi-times'"
              ></i>
              Al menos una letra mayúscula
            </li>
            <li :class="{ valid: passwordRegex.lowercase.test(newPassword) }">
              <i
                :class="passwordRegex.lowercase.test(newPassword) ? 'pi pi-check' : 'pi pi-times'"
              ></i>
              Al menos una letra minúscula
            </li>
            <li :class="{ valid: passwordRegex.number.test(newPassword) }">
              <i
                :class="passwordRegex.number.test(newPassword) ? 'pi pi-check' : 'pi pi-times'"
              ></i>
              Al menos un número
            </li>
            <li :class="{ valid: passwordRegex.special.test(newPassword) }">
              <i
                :class="passwordRegex.special.test(newPassword) ? 'pi pi-check' : 'pi pi-times'"
              ></i>
              Al menos un carácter especial
            </li>
            <li :class="{ valid: newPassword !== oldPassword }">
              <i :class="newPassword !== oldPassword ? 'pi pi-check' : 'pi pi-times'"></i>
              Diferente a la contraseña actual
            </li>
          </ul>
        </div>
      </div>

      <!-- Confirm Password Field -->
      <div class="form-field">
        <label for="confirm_password" class="form-label">
          Confirmar Nueva Contraseña <span class="required">*</span>
        </label>
        <div class="password-input-wrapper">
          <InputText
            id="confirm_password"
            v-model="confirmPassword"
            :type="showConfirmPassword ? 'text' : 'password'"
            placeholder="Confirma tu nueva contraseña"
            :class="{ 'p-invalid': errors.confirmPassword }"
            autocomplete="new-password"
            class="password-input"
          />
          <Button
            :icon="showConfirmPassword ? 'pi pi-eye-slash' : 'pi pi-eye'"
            severity="secondary"
            text
            type="button"
            @click="showConfirmPassword = !showConfirmPassword"
            class="toggle-password-btn"
            tabindex="-1"
          />
        </div>
        <small v-if="errors.confirmPassword" class="error-text">
          {{ errors.confirmPassword }}
        </small>
      </div>

      <!-- Actions -->
      <div class="modal-actions">
        <Button
          label="Cancelar"
          severity="secondary"
          outlined
          type="button"
          @click="handleClose(false)"
          :disabled="isChangePasswordPending"
        />
        <Button
          label="Cambiar Contraseña"
          icon="pi pi-lock"
          type="submit"
          :loading="isChangePasswordPending"
          :disabled="!isFormValid || isChangePasswordPending"
        />
      </div>
    </form>
  </DefaultModal>
</template>

<style scoped>
.change-password-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 0.5rem 0;
}

.error-message {
  margin-bottom: 0.5rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-weight: 600;
  color: var(--vt-c-gray-700);
  font-size: 0.875rem;
}

.required {
  color: var(--color-danger);
}

.password-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

:deep(.password-input) {
  flex: 1;
  border: 2px solid var(--vt-c-gray-200);
  border-radius: 0.5rem;
  padding: 0.75rem;
  padding-right: 3rem;
  transition: all 0.3s ease;
  font-size: 0.875rem;
}

:deep(.password-input:focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 10%, transparent);
}

:deep(.password-input.p-invalid) {
  border-color: var(--color-danger);
}

:deep(.password-input.p-invalid:focus) {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-danger) 10%, transparent);
}

.toggle-password-btn {
  position: absolute;
  right: 0.25rem;
  color: var(--vt-c-gray-500);
  padding: 0.5rem;
}

:deep(.toggle-password-btn:hover) {
  background: var(--vt-c-gray-100);
}

.error-text {
  color: var(--color-danger);
  font-size: 0.75rem;
  font-weight: 500;
  margin-top: -0.25rem;
}

/* Password Strength Indicator */
.password-strength {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.strength-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.strength-label {
  font-size: 0.75rem;
  color: var(--vt-c-gray-500);
  font-weight: 500;
}

.strength-value {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.strength-value.strength-danger {
  color: var(--color-danger);
}

.strength-value.strength-warning {
  color: var(--color-warning);
}

.strength-value.strength-info {
  color: var(--color-info);
}

.strength-value.strength-success {
  color: var(--color-success);
}

:deep(.strength-bar-danger .p-progressbar-value) {
  background: var(--color-danger);
}

:deep(.strength-bar-warning .p-progressbar-value) {
  background: var(--color-warning);
}

:deep(.strength-bar-info .p-progressbar-value) {
  background: var(--color-info);
}

:deep(.strength-bar-success .p-progressbar-value) {
  background: var(--color-success);
}

:deep(.p-progressbar) {
  height: 0.5rem;
  border-radius: 0.25rem;
  background: var(--vt-c-gray-200);
}

/* Password Requirements */
.password-requirements {
  margin-top: 0.5rem;
  padding: 1rem;
  background: var(--vt-c-gray-50);
  border-radius: 0.5rem;
  border: 1px solid var(--vt-c-gray-200);
}

.requirements-title {
  margin: 0 0 0.75rem 0;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--vt-c-gray-600);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.requirements-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.requirements-list li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--vt-c-gray-500);
  transition: all 0.3s ease;
}

.requirements-list li i {
  font-size: 0.625rem;
  color: var(--vt-c-gray-400);
  transition: all 0.3s ease;
}

.requirements-list li.valid {
  color: var(--color-success);
  font-weight: 500;
}

.requirements-list li.valid i {
  color: var(--color-success);
}

/* Modal Actions */
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--vt-c-gray-200);
  margin-top: 0.5rem;
}

/* Responsive */
@media (max-width: 640px) {
  .modal-actions {
    flex-direction: column-reverse;
  }

  .modal-actions button {
    width: 100%;
  }
}
</style>
