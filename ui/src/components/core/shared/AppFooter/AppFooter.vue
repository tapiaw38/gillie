<script setup lang="ts">
const currentYear = new Date().getFullYear()
const socialLinks = [
  {
    icon: 'pi pi-facebook',
    url: 'https://www.facebook.com/gillie-app',
  },
  {
    icon: 'pi pi-twitter',
    url: 'https://twitter.com/gillie-app',
  },
  {
    icon: 'pi pi-instagram',
    url: 'https://www.instagram.com/gillie-app',
  },
  {
    icon: 'pi pi-linkedin',
    url: 'https://www.linkedin.com/company/gillie-app',
  },
]
</script>

<template>
  <footer class="app-footer">
    <!-- Decorative shapes -->
    <div class="footer-shapes">
      <div class="footer-shape footer-shape-1"></div>
      <div class="footer-shape footer-shape-2"></div>
    </div>

    <div class="container">
      <div class="footer-content">
        <div class="footer-section">
          <h3>Gillie App</h3>
          <p>
            Automatiza tu negocio con inteligencia artificial. Gillie te ayuda a integrar IA en tu
            sitio web, canales de atención y sistemas de trabajo para aumentar la productividad y
            mejorar la experiencia de tus clientes.
          </p>
        </div>

        <div class="footer-section">
          <h3>Síguenos</h3>
          <ul class="social-links">
            <li v-for="link in socialLinks" :key="link.url">
              <a :href="link.url" target="_blank" rel="noopener noreferrer">
                <i :class="link.icon" />
              </a>
            </li>
          </ul>
        </div>

        <div class="footer-section">
          <h3>Enlaces</h3>
          <ul class="footer-links">
            <li><a href="/privacy-policy">Política de Privacidad</a></li>
            <li><a href="/terms-of-service">Términos de Servicio</a></li>
            <li><a href="/contact">Contáctanos</a></li>
            <li><a href="/about">Acerca de</a></li>
          </ul>
        </div>
      </div>

      <div class="footer-bottom">
        <p>&copy; {{ currentYear }} Gillie App. Todos los derechos reservados.</p>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  padding: 4rem 0 2rem 0;
  color: white;
  position: relative;
  overflow: hidden;
}

.app-footer::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.15) 50%,
    transparent 100%
  );
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
  position: relative;
  z-index: 2;
}

.footer-content {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 2rem;
  align-items: start;
}

.footer-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.footer-section:first-child {
  max-width: 350px;
}

.footer-section:first-child p {
  font-size: 0.9375rem;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.7);
  margin: 0;
  font-weight: 300;
}

.footer-section h3 {
  font-size: 1rem;
  font-weight: 600;
  color: white;
  margin: 0 0 1rem 0;
  letter-spacing: 0.01em;
}

/* Social Links - using PrimeVue classes */
.social-links {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  gap: 0.75rem;
}

.social-links li a {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  color: rgba(255, 255, 255, 0.7);
  font-size: 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.625rem;
  transition: all 0.4s cubic-bezier(0.83, 0, 0.17, 1);
  text-decoration: none;
}

.social-links li a:hover {
  color: white;
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-3px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

/* Footer Links - using PrimeVue classes */
.footer-links {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.footer-links li a {
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  font-weight: 400;
  padding: 0.5rem 0.875rem;
  border-radius: 0.5rem;
  transition: all 0.4s cubic-bezier(0.83, 0, 0.17, 1);
  display: inline-block;
  font-size: 0.9375rem;
  letter-spacing: 0.01em;
}

.footer-links li a:hover {
  color: white;
  background: rgba(255, 255, 255, 0.08);
  transform: translateX(4px);
}

.footer-bottom {
  margin-top: 2.5rem;
  padding-top: 1.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  text-align: center;
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.875rem;
  font-weight: 300;
}

/* Decorative elements */
.footer-shapes {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  pointer-events: none;
}

.footer-shape {
  position: absolute;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.08));
  animation: float 12s cubic-bezier(0.83, 0, 0.17, 1) infinite;
  filter: blur(40px);
  border-radius: 50%;
}

.footer-shape-1 {
  width: 300px;
  height: 300px;
  top: -10%;
  right: 5%;
  animation-delay: 0s;
}

.footer-shape-2 {
  width: 250px;
  height: 250px;
  bottom: -10%;
  left: 10%;
  animation-delay: 6s;
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.1), rgba(236, 72, 153, 0.08));
}

@keyframes float {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.3;
  }
  50% {
    transform: translate(-20px, -30px) scale(1.1);
    opacity: 0.5;
  }
}

/* Responsive Design */
@media (max-width: 768px) {
  .app-footer {
    padding: 2rem 0 1rem 0;
  }

  .container {
    padding: 0 1.25rem;
  }

  .footer-content {
    grid-template-columns: 1fr;
    gap: 1.5rem;
    text-align: center;
  }

  .footer-section:first-child {
    max-width: none;
  }

  .social-links {
    justify-content: center;
  }

  .footer-links {
    align-items: center;
  }

  .footer-links li a {
    text-align: center;
    min-width: 180px;
  }
}

@media (max-width: 480px) {
  .app-footer {
    padding: 1.5rem 0 0.75rem 0;
  }

  .container {
    padding: 0 1rem;
  }

  .footer-content {
    gap: 1.25rem;
  }

  .social-links li a {
    width: 2.25rem;
    height: 2.25rem;
    font-size: 1rem;
  }

  .footer-links li a {
    min-width: 160px;
    padding: 0.5rem 0.75rem;
  }
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
  .footer-shape {
    animation: none;
  }

  .social-links li a:hover,
  .footer-links li a:hover {
    transform: none;
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .app-footer {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  }
}
</style>
