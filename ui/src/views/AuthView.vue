<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Toast from 'primevue/toast'
import AuthLogin from '@/components/core/AuthLogin/AuthLogin.vue'
import AuthRegister from '@/components/core/AuthRegister/AuthRegister.vue'
import ForgotPassword from '@/components/core/ForgotPassword/ForgotPassword.vue'
import { useAuth } from '@/composables/useAuth'
import LoadingSpinner from '@/components/core/LoadingSpinner/LoadingSpinner.vue'
import GoogleButton from '@/components/core/GoogleButton/GoogleButton.vue'
import Button from 'primevue/button'

const router = useRouter()
const toast = useToast()

const { isLoginPending, isLoginError, isLoginSuccess, loginUser, meUser, user } = useAuth()

type ViewMode = 'login' | 'register' | 'forgot-password'
const currentView = ref<ViewMode>('login')

const toggleView = () => {
  currentView.value = currentView.value === 'login' ? 'register' : 'login'
}

const showForgotPassword = () => {
  currentView.value = 'forgot-password'
}

const backToLogin = () => {
  currentView.value = 'login'
}

const loginWithGoogle = async (code: string) => {
  try {
    await loginUser({ ssoType: 'google', ssoCode: code })
    await new Promise((resolve) => setTimeout(resolve, 100))
    if (isLoginSuccess.value) {
      if (!user.value) {
        await meUser()
      }
      await router.push('/dashboard')
    }
  } catch (error) {
    console.error('Error during Google login:', error)
  }
}

watch(isLoginSuccess, (value) => {
  if (value) {
    toast.add({
      severity: 'success',
      summary: 'Inicio de sesión exitoso',
      detail: 'Bienvenido de vuelta',
      life: 3000,
    })
  }
})
</script>

<template>
  <div class="auth-container">
    <div class="auth-background">
      <div class="auth-shapes">
        <div class="shape shape-2"></div>
        <div class="shape shape-3"></div>
      </div>
    </div>

    <div class="auth-content">
      <div class="auth-header">
        <div class="logo-container">
          <div class="logo-icon">
            <i class="pi pi-sparkles"></i>
          </div>
          <h1 class="logo-text">Gillie Assistant</h1>
        </div>
        <p class="auth-subtitle">
          {{
            currentView === 'login'
              ? 'Bienvenido de vuelta'
              : currentView === 'register'
                ? 'Únete a nosotros'
                : 'Recupera tu cuenta'
          }}
        </p>
      </div>

      <Card class="auth-card">
        <template #content>
          <div class="auth-form-container">
            <div class="form-header">
              <div class="form-icon">
                <i
                  :class="
                    currentView === 'login'
                      ? 'pi pi-sign-in'
                      : currentView === 'register'
                        ? 'pi pi-user-plus'
                        : 'pi pi-key'
                  "
                ></i>
              </div>
              <h2 class="form-title">
                {{
                  currentView === 'login'
                    ? 'Iniciar Sesión'
                    : currentView === 'register'
                      ? 'Crear Cuenta'
                      : 'Recuperar Contraseña'
                }}
              </h2>
            </div>

            <div class="form-content">
              <template v-if="currentView === 'login'">
                <AuthLogin @show-forgot-password="showForgotPassword" />
              </template>
              <template v-else-if="currentView === 'register'">
                <AuthRegister />
              </template>
              <template v-else>
                <ForgotPassword @back-to-login="backToLogin" />
              </template>
            </div>

            <!-- Only show divider and Google button for login/register -->
            <template v-if="currentView !== 'forgot-password'">
              <div class="divider">
                <span class="divider-text">o continúa con</span>
              </div>

              <div class="social-login">
                <GoogleButton @code="loginWithGoogle" />
              </div>

              <div class="form-footer">
                <p class="toggle-text">
                  {{
                    currentView === 'login' ? '¿No tienes una cuenta?' : '¿Ya tienes una cuenta?'
                  }}
                  <Button
                    :label="currentView === 'login' ? 'Crear cuenta' : 'Iniciar sesión'"
                    text
                    severity="secondary"
                    class="p-button-link"
                    @click="toggleView"
                  />
                </p>
              </div>
            </template>
          </div>
        </template>
      </Card>

      <!-- Loading State -->
      <div v-if="isLoginPending" class="loading-overlay">
        <div class="loading-content">
          <LoadingSpinner />
          <p class="loading-text">Iniciando sesión...</p>
        </div>
      </div>

      <!-- Error State -->
      <div v-if="isLoginError" class="error-message">
        <i class="pi pi-exclamation-triangle"></i>
        <span>Error al iniciar sesión. Intenta nuevamente.</span>
      </div>
    </div>

    <!-- Toast for Notifications -->
    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.auth-container {
  min-height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: var(--gradient-background);
}

/* Animated Background */
.auth-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
}

.auth-shapes {
  position: relative;
  width: 100%;
  height: 100%;
}

.shape {
  position: absolute;
  background: rgba(255, 255, 255, 0.1);
  animation: float 6s ease-in-out infinite;
  filter: drop-shadow(0 0 30px rgba(255, 255, 255, 0.2));
}

.shape-2 {
  width: 220px;
  height: 220px;
  top: 60%;
  right: 10%;
  animation-delay: 2s;
  clip-path: polygon(
    30% 0%,
    70% 0%,
    100% 30%,
    100% 70%,
    70% 100%,
    30% 100%,
    0% 70%,
    0% 30%,
    20% 20%,
    50% 10%,
    80% 20%,
    80% 80%,
    50% 90%,
    20% 80%
  );
}

.shape-3 {
  width: 180px;
  height: 180px;
  bottom: 20%;
  left: 60%;
  animation-delay: 4s;
  clip-path: polygon(
    50% 0%,
    65% 10%,
    80% 25%,
    90% 40%,
    95% 55%,
    90% 70%,
    75% 85%,
    60% 95%,
    45% 100%,
    30% 95%,
    15% 85%,
    5% 70%,
    0% 55%,
    5% 40%,
    15% 25%,
    30% 10%
  );
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0px) rotate(0deg) scale(1);
  }
  33% {
    transform: translateY(-20px) rotate(120deg) scale(1.05);
  }
  66% {
    transform: translateY(-12px) rotate(240deg) scale(0.95);
  }
}

/* Main Content */
.auth-content {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 450px;
  padding: 2rem;
}

/* Header */
.auth-header {
  text-align: center;
  margin-bottom: 2rem;
}

.logo-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.logo-icon {
  width: 4rem;
  height: 4rem;
  background: var(--gradient-primary);
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 32px rgba(37, 99, 235, 0.3);
}

.logo-icon i {
  font-size: 2rem;
  color: var(--vt-c-white);
}

.logo-text {
  font-size: 2rem;
  font-weight: 700;
  color: var(--vt-c-white);
  margin: 0;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.auth-subtitle {
  font-size: 1.125rem;
  color: rgba(255, 255, 255, 0.9);
  margin: 0;
  font-weight: 400;
}

/* Auth Card - using PrimeVue classes */
.auth-card {
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.95);
}

.auth-form-container {
  padding: 2.5rem;
}

/* Form Header */
.form-header {
  text-align: center;
  margin-bottom: 2rem;
}

.form-icon {
  width: 3.5rem;
  height: 3.5rem;
  background: var(--gradient-primary);
  border-radius: 1rem;
  margin: 0 auto 1rem auto;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 32px rgba(37, 99, 235, 0.3);
}

.form-icon i {
  font-size: 1.5rem;
  color: var(--vt-c-white);
}

.form-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--vt-c-gray-800);
  margin: 0;
}

/* Form Content */
.form-content {
  margin-bottom: 2rem;
}

/* Divider */
.divider {
  position: relative;
  text-align: center;
  margin: 2rem 0;
}

.divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--vt-c-gray-200);
}

.divider-text {
  background: var(--vt-c-white);
  padding: 0 1rem;
  color: var(--vt-c-gray-500);
  font-size: 0.875rem;
  font-weight: 500;
  position: relative;
  z-index: 1;
}

/* Social Login */
.social-login {
  margin-bottom: 2rem;
}

/* Form Footer */
.form-footer {
  text-align: center;
}

.toggle-text {
  color: var(--vt-c-gray-500);
  font-size: 0.875rem;
  margin: 0;
}

/* Toggle button - using PrimeVue button classes */

/* Loading Overlay */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.loading-content {
  background: var(--vt-c-white);
  padding: 2rem;
  border-radius: 1rem;
  text-align: center;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.loading-text {
  color: var(--vt-c-gray-700);
  font-weight: 500;
  margin: 0;
}

/* Error Message */
.error-message {
  margin-top: 1rem;
  padding: 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 0.75rem;
  color: var(--vt-c-danger-dark);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  backdrop-filter: blur(10px);
}

.error-message i {
  font-size: 1.125rem;
}

/* Responsive Design */
@media (max-width: 768px) {
  .auth-content {
    padding: 1rem;
    max-width: 100%;
  }

  .auth-form-container {
    padding: 2rem 1.5rem;
  }

  .logo-text {
    font-size: 1.75rem;
  }

  .logo-icon {
    width: 3rem;
    height: 3rem;
  }

  .logo-icon i {
    font-size: 1.5rem;
  }

  .form-icon {
    width: 3rem;
    height: 3rem;
  }

  .form-icon i {
    font-size: 1.25rem;
  }

  .form-title {
    font-size: 1.5rem;
  }

  .shape-1 {
    width: 200px;
    height: 200px;
  }

  .shape-2 {
    width: 150px;
    height: 150px;
  }

  .shape-3 {
    width: 100px;
    height: 100px;
  }
}

@media (max-width: 480px) {
  .auth-content {
    padding: 0.5rem;
  }

  .auth-form-container {
    padding: 1.5rem 1rem;
  }

  .logo-container {
    flex-direction: column;
    gap: 0.5rem;
  }

  .logo-text {
    font-size: 1.5rem;
  }

  .loading-content {
    margin: 1rem;
    padding: 1.5rem;
  }
}

/* Enhanced animations */
.auth-card {
  animation: slideUp 0.6s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.form-icon {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}
</style>
