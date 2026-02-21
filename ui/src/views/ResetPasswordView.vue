<script setup lang="ts">
import Card from 'primevue/card'
import ResetPassword from '@/components/core/ResetPassword/ResetPassword.vue'
</script>

<template>
  <div class="reset-password-view-container">
    <div class="reset-password-background">
      <div class="reset-password-shapes">
        <div class="shape shape-2"></div>
        <div class="shape shape-3"></div>
      </div>
    </div>

    <div class="reset-password-content">
      <div class="reset-password-header">
        <div class="logo-container">
          <div class="logo-icon">
            <i class="pi pi-sparkles"></i>
          </div>
          <h1 class="logo-text">Gillie Assistant</h1>
        </div>
        <p class="auth-subtitle">Recuperación de contraseña</p>
      </div>

      <Card class="reset-password-card">
        <template #content>
          <div class="form-container">
            <ResetPassword />
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.reset-password-view-container {
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
.reset-password-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
}

.reset-password-shapes {
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
.reset-password-content {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 500px;
  padding: 2rem;
}

/* Header */
.reset-password-header {
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

/* Card */
.reset-password-card {
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.95);
}

.form-container {
  padding: 2rem;
}

/* Responsive Design */
@media (max-width: 768px) {
  .reset-password-content {
    padding: 1rem;
    max-width: 100%;
  }

  .form-container {
    padding: 1.5rem;
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
  .reset-password-content {
    padding: 0.5rem;
  }

  .form-container {
    padding: 1.5rem 1rem;
  }

  .logo-container {
    flex-direction: column;
    gap: 0.5rem;
  }

  .logo-text {
    font-size: 1.5rem;
  }
}

/* Enhanced animations */
.reset-password-card {
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
</style>
