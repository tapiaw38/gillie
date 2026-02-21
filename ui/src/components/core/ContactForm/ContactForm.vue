<script setup lang="ts">
import { ref, reactive } from 'vue'
import emailjs from '@emailjs/browser'
import { useToast } from 'primevue/usetoast'

import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Toast from 'primevue/toast'

const SERVICE_ID = import.meta.env.VITE_EMAILJS_SERVICE_ID
const TEMPLATE_ID = import.meta.env.VITE_EMAILJS_TEMPLATE_ID
const PUBLIC_KEY = import.meta.env.VITE_EMAILJS_PUBLIC_KEY

const toast = useToast()
const formRef = ref<HTMLFormElement | null>(null)
const loading = ref(false)

const form = reactive({
  user_name: '',
  user_email: '',
  message: '',
})

const sendEmail = async () => {
  if (!formRef.value) return

  if (!form.user_name.trim() || !form.user_email.trim() || !form.message.trim()) {
    toast.add({
      severity: 'warn',
      summary: 'Campos requeridos',
      detail: 'Por favor completa todos los campos del formulario',
      life: 3000,
    })
    return
  }

  loading.value = true

  try {
    await emailjs.sendForm(SERVICE_ID, TEMPLATE_ID, formRef.value, PUBLIC_KEY)

    toast.add({
      severity: 'success',
      summary: 'Mensaje enviado',
      detail: '¡Tu mensaje se envió con éxito! Nos pondremos en contacto contigo pronto.',
      life: 4000,
    })

    form.user_name = ''
    form.user_email = ''
    form.message = ''
  } catch (error) {
    console.error('EmailJS Error:', error)

    toast.add({
      severity: 'error',
      summary: 'Error al enviar mensaje',
      detail: 'Hubo un problema al enviar tu mensaje. Por favor intenta nuevamente.',
      life: 4000,
    })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="contact-form-container">
    <!-- Header Section -->
    <div class="form-header">
      <div class="header-icon">
        <i class="pi pi-envelope"></i>
      </div>
      <div class="header-content">
        <h3 class="form-title">Envíanos un mensaje</h3>
        <p class="form-description">
          Completa el formulario y nos pondremos en contacto contigo lo antes posible.
        </p>
      </div>
    </div>

    <!-- Contact Form -->
    <div class="form-wrapper">
      <form @submit.prevent="sendEmail" ref="formRef" class="contact-form">
        <div class="form-grid">
          <!-- Name Field -->
          <div class="form-field">
            <label for="name" class="field-label">
              <i class="pi pi-user field-icon"></i>
              Nombre completo
            </label>
            <div class="input-wrapper">
              <InputText
                id="name"
                v-model="form.user_name"
                name="user_name"
                class="modern-input"
                placeholder="Ej: Juan Pérez"
                required
              />
            </div>
          </div>

          <!-- Email Field -->
          <div class="form-field">
            <label for="email" class="field-label">
              <i class="pi pi-at field-icon"></i>
              Correo electrónico
            </label>
            <div class="input-wrapper">
              <InputText
                id="email"
                v-model="form.user_email"
                name="user_email"
                type="email"
                class="modern-input"
                placeholder="Ej: juan@empresa.com"
                required
              />
            </div>
          </div>
        </div>

        <!-- Message Field -->
        <div class="form-field message-field">
          <label for="message" class="field-label">
            <i class="pi pi-comment field-icon"></i>
            Mensaje
          </label>
          <div class="input-wrapper">
            <Textarea
              id="message"
              v-model="form.message"
              name="message"
              :rows="6"
              class="modern-textarea"
              placeholder="Cuéntanos sobre tu proyecto o consulta..."
              required
            />
          </div>
          <small class="field-help">
            Describe tu consulta o proyecto para poder ayudarte mejor
          </small>
        </div>

        <!-- Submit Button -->
        <div class="form-actions">
          <Button type="submit" severity="primary" :loading="loading" :disabled="loading">
            <template #default>
              <i class="pi pi-send"></i>
              <span>{{ loading ? 'Enviando...' : 'Enviar Mensaje' }}</span>
            </template>
          </Button>
        </div>
      </form>
    </div>

    <!-- Contact Info -->
    <div class="contact-info">
      <div class="info-grid">
        <div class="info-item">
          <div class="info-icon">
            <i class="pi pi-clock"></i>
          </div>
          <div class="info-content">
            <h4>Tiempo de respuesta</h4>
            <p>Respondemos en menos de 24 horas</p>
          </div>
        </div>

        <div class="info-item">
          <div class="info-icon">
            <i class="pi pi-shield"></i>
          </div>
          <div class="info-content">
            <h4>Información segura</h4>
            <p>Tus datos están protegidos</p>
          </div>
        </div>

        <div class="info-item">
          <div class="info-icon">
            <i class="pi pi-users"></i>
          </div>
          <div class="info-content">
            <h4>Soporte personalizado</h4>
            <p>Atención directa de nuestro equipo</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Toast for Notifications -->
    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.contact-form-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 3rem;
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #f1f5f9;
}

/* Header Section */
.form-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 3rem;
  text-align: center;
  justify-content: center;
}

.header-icon {
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 0.75rem;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  color: white;
  box-shadow: 0 2px 12px rgba(99, 102, 241, 0.3);
  flex-shrink: 0;
}

.header-content {
  flex: 1;
}

.form-title {
  font-size: clamp(1.75rem, 3vw, 2rem);
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 0.5rem 0;
  letter-spacing: -0.01em;
}

.form-description {
  font-size: 1rem;
  color: #64748b;
  margin: 0;
  line-height: 1.7;
  font-weight: 300;
}

/* Form Wrapper */
.form-wrapper {
  margin-bottom: 3rem;
}

.contact-form {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Form Grid */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

/* Form Fields */
.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.message-field {
  grid-column: 1 / -1;
}

.field-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9375rem;
  font-weight: 500;
  color: #0f172a;
  letter-spacing: 0.01em;
}

.field-icon {
  color: #6366f1;
  font-size: 1rem;
}

.input-wrapper {
  position: relative;
}

/* Modern Inputs - using PrimeVue classes */
:deep(.modern-input),
:deep(.modern-textarea) {
  width: 100%;
  padding: 0.875rem 1.125rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.625rem;
  font-size: 0.9375rem;
  transition: all 0.4s cubic-bezier(0.83, 0, 0.17, 1);
  background: #fafbfc;
  color: #0f172a;
  font-family: inherit;
}

:deep(.modern-input:focus),
:deep(.modern-textarea:focus) {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08);
  background: white;
  outline: none;
}

:deep(.modern-input::placeholder),
:deep(.modern-textarea::placeholder) {
  color: #94a3b8;
  font-weight: 300;
}

:deep(.modern-textarea) {
  resize: vertical;
  min-height: 120px;
  line-height: 1.7;
}

.field-help {
  color: #64748b;
  font-size: 0.8125rem;
  font-style: normal;
  margin-top: 0.25rem;
  font-weight: 300;
}

/* Form Actions */
.form-actions {
  display: flex;
  justify-content: center;
  padding-top: 1rem;
}

/* Submit Button - using PrimeVue classes */
:deep(.p-button) {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border: none;
  border-radius: 0.625rem;
  padding: 1rem 3rem;
  font-weight: 500;
  font-size: 1rem;
  color: white;
  transition: all 0.4s cubic-bezier(0.83, 0, 0.17, 1);
  box-shadow: 0 2px 12px rgba(99, 102, 241, 0.3);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 200px;
  justify-content: center;
  letter-spacing: 0.01em;
}

:deep(.p-button:hover:not(:disabled)) {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
}

:deep(.p-button:disabled) {
  background: #94a3b8;
  box-shadow: none;
  cursor: not-allowed;
  transform: none;
  opacity: 0.6;
}

:deep(.p-button .pi) {
  font-size: 1rem;
}

/* Contact Info */
.contact-info {
  padding-top: 2.5rem;
  border-top: 1px solid #f1f5f9;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.5rem;
  background: #fafbfc;
  border-radius: 0.625rem;
  border: 1px solid #f1f5f9;
  transition: all 0.4s cubic-bezier(0.83, 0, 0.17, 1);
}

.info-item:hover {
  background: white;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
  border-color: #e2e8f0;
}

.info-icon {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 0.625rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.125rem;
  color: white;
  flex-shrink: 0;
}

.info-item:nth-child(1) .info-icon {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.info-item:nth-child(2) .info-icon {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.info-item:nth-child(3) .info-icon {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
}

.info-content {
  flex: 1;
}

.info-content h4 {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 0.25rem 0;
  letter-spacing: 0.01em;
}

.info-content p {
  font-size: 0.875rem;
  color: #64748b;
  margin: 0;
  line-height: 1.6;
  font-weight: 300;
}

/* Responsive Design */
@media (max-width: 768px) {
  .contact-form-container {
    padding: 1.5rem;
    margin: 1rem;
    border-radius: 1rem;
  }

  .form-header {
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .header-icon {
    width: 3rem;
    height: 3rem;
    font-size: 1.5rem;
  }

  .form-title {
    font-size: 1.75rem;
  }

  .form-description {
    font-size: 1rem;
  }

  .form-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .contact-form {
    gap: 1.5rem;
  }

  :deep(.modern-input),
  :deep(.modern-textarea) {
    padding: 0.875rem 1rem;
    font-size: 0.9rem;
  }

  :deep(.submit-button) {
    padding: 0.875rem 2rem;
    font-size: 1rem;
    width: 100%;
  }

  .info-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .info-item {
    padding: 1rem;
  }

  .info-icon {
    width: 2.5rem;
    height: 2.5rem;
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  .contact-form-container {
    padding: 1rem;
    margin: 0.5rem;
  }

  .form-title {
    font-size: 1.5rem;
  }

  .form-description {
    font-size: 0.9rem;
  }

  :deep(.modern-input),
  :deep(.modern-textarea) {
    padding: 0.75rem;
    border-radius: 0.5rem;
  }

  :deep(.submit-button) {
    padding: 0.75rem 1.5rem;
    border-radius: 0.5rem;
  }

  .info-item {
    flex-direction: column;
    text-align: center;
    gap: 0.75rem;
  }

  .info-icon {
    align-self: center;
  }
}

/* Loading Animation */
:deep(.submit-button .p-button-loading-icon) {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Focus States for Accessibility */
.info-item:focus-within {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
  .info-item,
  :deep(.submit-button),
  :deep(.modern-input),
  :deep(.modern-textarea) {
    transition: none;
  }

  .info-item:hover,
  :deep(.submit-button:hover) {
    transform: none;
  }

  :deep(.submit-button .p-button-loading-icon) {
    animation: none;
  }
}
</style>
