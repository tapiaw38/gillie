<template>
  <div class="about-container">
    <!-- Header Section -->
    <div class="header-section">
      <div class="about-header">
        <div class="icon-wrapper">
          <i class="pi pi-info-circle"></i>
        </div>
        <div class="header-content">
          <h1 class="page-title">Acerca de Gillie</h1>
          <p class="page-subtitle">Conoce más sobre nuestro asistente virtual</p>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="content-grid">
      <!-- About Card -->
      <Card class="about-card">
        <template #content>
          <div class="about-content">
            <div class="about-text">
              <h2>Nuestra Misión</h2>
              <p>
                En Gillie, nos dedicamos a transformar la experiencia del cliente mediante
                asistentes virtuales inteligentes que automatizan procesos, reducen tiempos de
                atención y mejoran la eficiencia operativa de tu negocio.
              </p>

              <h2>Nuestra Tecnología</h2>
              <p>
                Utilizamos las últimas tecnologías de procesamiento de lenguaje natural y
                aprendizaje automático para crear asistentes que comprenden el contexto, mantienen
                conversaciones naturales y resuelven problemas complejos de forma autónoma.
              </p>

              <h2>Integraciones</h2>
              <p>
                Nuestro sistema se integra fácilmente con WhatsApp Business, páginas web, sistemas
                CRM y APIs de terceros para ofrecer una experiencia de usuario coherente en todos
                los canales de comunicación.
              </p>
            </div>

            <div class="about-image">
              <div class="image-placeholder">
                <i class="pi pi-robot"></i>
                <span>Asistente Virtual</span>
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Features Card -->
      <Card class="features-card">
        <template #header>
          <div class="card-header">
            <div class="header-icon">
              <i class="pi pi-star"></i>
            </div>
            <div class="header-text">
              <h3>Características Principales</h3>
              <p>Lo que hace especial a Gillie</p>
            </div>
          </div>
        </template>
        <template #content>
          <div class="features-grid">
            <div class="feature-item">
              <div class="feature-icon">
                <i class="pi pi-brain"></i>
              </div>
              <div class="feature-content">
                <h4>Inteligencia Artificial Avanzada</h4>
                <p>
                  Modelos de lenguaje de última generación para respuestas precisas y naturales.
                </p>
              </div>
            </div>

            <div class="feature-item">
              <div class="feature-icon">
                <i class="pi pi-bolt"></i>
              </div>
              <div class="feature-content">
                <h4>Integraciones Personalizadas</h4>
                <p>Conexiones con APIs externas para realizar tareas complejas y automatizadas.</p>
              </div>
            </div>

            <div class="feature-item">
              <div class="feature-icon">
                <i class="pi pi-shield"></i>
              </div>
              <div class="feature-content">
                <h4>Seguridad de Datos</h4>
                <p>
                  Políticas de privacidad y encriptación de extremo a extremo para proteger la
                  información.
                </p>
              </div>
            </div>

            <div class="feature-item">
              <div class="feature-icon">
                <i class="pi pi-chart-line"></i>
              </div>
              <div class="feature-content">
                <h4>Analítica Avanzada</h4>
                <p>
                  Seguimiento detallado de interacciones para optimizar la experiencia del usuario.
                </p>
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Contact Card -->
      <Card class="contact-card">
        <template #header>
          <div class="card-header">
            <div class="header-icon">
              <i class="pi pi-envelope"></i>
            </div>
            <div class="header-text">
              <h3>¿Tienes preguntas?</h3>
              <p>Contacta con nuestro equipo de soporte</p>
            </div>
          </div>
        </template>
        <template #content>
          <div class="contact-content">
            <p>¿Quieres más información sobre Gillie o necesitas ayuda con tu asistente?</p>
            <div class="contact-actions">
              <Button
                label="Contactar Soporte"
                icon="pi pi-comments"
                class="p-button-text"
                @click="contactSupport"
              />
              <Button
                label="Programar Demo"
                icon="pi pi-calendar"
                severity="primary"
                outlined
                @click="scheduleDemo"
              />
            </div>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import Card from 'primevue/card'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'

const toast = useToast()

const contactSupport = () => {
  toast.add({
    severity: 'info',
    summary: 'Contactar Soporte',
    detail: 'Enviaremos un correo a nuestro equipo de soporte para que te contacten pronto.',
    life: 4000,
  })
}

const scheduleDemo = () => {
  toast.add({
    severity: 'success',
    summary: 'Demo Programada',
    detail: 'Hemos registrado tu solicitud. Un representante se pondrá en contacto contigo.',
    life: 4000,
  })
}
</script>

<style scoped>
.about-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
}

/* Header Section */
.header-section {
  margin-bottom: 2rem;
}

.about-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.icon-wrapper {
  width: 4rem;
  height: 4rem;
  border-radius: 1rem;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: white;
  box-shadow: var(--shadow-primary);
}

.header-content {
  flex: 1;
}

.page-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 0.5rem 0;
  background: linear-gradient(135deg, #1e293b 0%, #475569 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-subtitle {
  font-size: 1.125rem;
  color: #64748b;
  margin: 0;
  font-weight: 400;
}

/* Content Grid */
.content-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
}

/* About Card */
.about-card {
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.about-card:hover {
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

:deep(.about-card .p-card-content) {
  padding: 2rem;
}

.about-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2rem;
}

.about-text h2 {
  color: #1e293b;
  font-size: 1.5rem;
  margin: 1.5rem 0 1rem 0;
  font-weight: 600;
  position: relative;
}

.about-text h2:first-child {
  margin-top: 0;
}

.about-text h2::after {
  content: '';
  position: absolute;
  bottom: -0.5rem;
  left: 0;
  width: 4rem;
  height: 0.25rem;
  background: var(--gradient-primary);
  border-radius: 0.125rem;
}

.about-text p {
  color: #64748b;
  line-height: 1.7;
  margin-bottom: 1.5rem;
}

.about-image {
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-placeholder {
  width: 100%;
  height: 250px;
  border-radius: 1rem;
  background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  border: 2px dashed #a5b4fc;
}

.image-placeholder i {
  font-size: 4rem;
  color: var(--color-primary);
}

.image-placeholder span {
  font-size: 1.125rem;
  color: var(--color-primary-dark);
  font-weight: 600;
}

/* Features Card */
.features-card {
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.features-card:hover {
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

:deep(.features-card .p-card-header) {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e2e8f0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  background: var(--gradient-info);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  color: white;
}

.header-text h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-info-dark);
}

.header-text p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--color-info);
}

:deep(.features-card .p-card-content) {
  padding: 2rem;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.feature-item {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  background: #f8fafc;
  border-radius: 0.75rem;
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.feature-item:hover {
  background: white;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.feature-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--color-info);
  font-size: 1.25rem;
}

.feature-content h4 {
  margin: 0 0 0.5rem 0;
  color: #1e293b;
  font-size: 1.125rem;
  font-weight: 600;
}

.feature-content p {
  margin: 0;
  color: #64748b;
  font-size: 0.875rem;
  line-height: 1.6;
}

/* Contact Card */
.contact-card {
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.contact-card:hover {
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

:deep(.contact-card .p-card-header) {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e2e8f0;
}

:deep(.contact-card .p-card-content) {
  padding: 2rem;
}

.contact-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  text-align: center;
}

.contact-content p {
  color: #64748b;
  font-size: 1.125rem;
  margin: 0;
  line-height: 1.7;
}

.contact-actions {
  display: flex;
  gap: 1rem;
  width: 100%;
  justify-content: center;
}

/* Responsive Design */
@media (max-width: 768px) {
  .about-container {
    padding: 1rem;
  }

  .about-header {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .page-title {
    font-size: 2rem;
  }

  .page-subtitle {
    font-size: 1rem;
  }

  .about-content {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .contact-actions {
    flex-direction: column;
    align-items: center;
  }

  :deep(.about-card .p-card-content),
  :deep(.features-card .p-card-content),
  :deep(.contact-card .p-card-content) {
    padding: 1.5rem;
  }

  :deep(.features-card .p-card-header),
  :deep(.contact-card .p-card-header) {
    padding: 1rem 1.5rem;
  }

  .image-placeholder {
    height: 200px;
  }
}

@media (max-width: 480px) {
  .about-container {
    padding: 0.5rem;
  }

  .icon-wrapper {
    width: 3rem;
    height: 3rem;
    font-size: 1.5rem;
  }

  .page-title {
    font-size: 1.75rem;
  }

  :deep(.about-card .p-card-content),
  :deep(.features-card .p-card-content),
  :deep(.contact-card .p-card-content) {
    padding: 1rem;
  }

  :deep(.features-card .p-card-header),
  :deep(.contact-card .p-card-header) {
    padding: 1rem;
  }

  .feature-item {
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
  }

  .contact-actions {
    width: 100%;
  }
}
</style>
