<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useClipboard } from '@/composables/useClipboard'
import Card from 'primevue/card'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import Prism from 'prismjs'

const codeConfigBlock = ref<HTMLElement | null>(null)
const codeMethodsBlock = ref<HTMLElement | null>(null)
const toast = useToast()
const { copyText } = useClipboard()

const copyToClipboard = async (text: string, type: string) => {
  try {
    const copied = await copyText(text)
    if (!copied) {
      throw new Error('clipboard_unavailable')
    }
    toast.add({
      severity: 'success',
      summary: 'Código copiado',
      detail: `${type} copiado al portapapeles`,
      life: 3000,
    })
  } catch (error) {
    console.log(error)
    toast.add({
      severity: 'error',
      summary: 'Error al copiar',
      detail: 'No se pudo copiar el código al portapapeles',
      life: 3000,
    })
  }
}

const codeConfig = `// Assistant with full configuration
const assistant = createAssistant({
  // API Key for the assistant (required)
  apiKey: "your-api-key",
  // API URL for the assistant server (required)
  apiBaseUrl: "your-base-url",
  // General options
  title: "My Assistant",
  placeholder: "How can I help you?",
  position: "bottom-right", // 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'
  initialMessage: "Hello! I am your virtual assistant. How can I help you?",
  autoOpen: false, // If true, the chat will open automatically

  // Specific button options
  buttonOptions: {
    backgroundColor: "#4a90e2",
    color: "#ffffff",
    icon: "💬", // Emoticon or HTML for the button
    size: "medium", // 'small' | 'medium' | 'large'
    container: "#my-container", // Selector or element where to mount the button
  },

  // Chat theme options
  theme: {
    primaryColor: "#4a90e2", // Primary color (header and send button)
    textColor: "#333333", // General text color
    backgroundColor: "#ffffff", // Chat background color
    userMessageBgColor: "#4a90e2", // User message background color
    userMessageTextColor: "#ffffff", // User message text color
    assistantMessageBgColor: "#f1f1f1", // Assistant message background color
    assistantMessageTextColor: "#333333", // Assistant message text color
    inputBorderColor: "#e0e0e0", // Input border color
    inputBgColor: "#ffffff", // Input background color
    inputTextColor: "#333333", // Input text color
  },
});
`

const codeMethods = `// Open the chat
assistant.open();

// Close the chat
assistant.close();

// Toggle between open/closed
assistant.toggle();

// Check if it's open
const isOpen = assistant.isOpen();

// Hide the floating button (for example, when using your own button)
assistant.hideButton();

// Show the floating button
assistant.showButton();

// Unmount the assistant (remove from the DOM)
assistant.unmount();
`

onMounted(() => {
  if (codeConfigBlock.value) {
    codeConfigBlock.value.innerHTML = codeConfig
    Prism.highlightElement(codeConfigBlock.value)
  }
  if (codeMethodsBlock.value) {
    codeMethodsBlock.value.innerHTML = codeMethods
    Prism.highlightElement(codeMethodsBlock.value)
  }
})

watch(codeConfigBlock, (newValue) => {
  if (newValue) {
    Prism.highlightElement(newValue)
  }
})
watch(codeMethodsBlock, (newValue) => {
  if (newValue) {
    Prism.highlightElement(newValue)
  }
})
</script>

<template>
  <div class="integration-container">
    <!-- Header Section -->
    <div class="header-section">
      <div class="integration-header">
        <div class="icon-wrapper web-icon">
          <i class="pi pi-globe"></i>
        </div>
        <div class="header-content">
          <h1 class="integration-title">Integración Web</h1>
          <p class="integration-subtitle">Integra tu asistente en sitios web y aplicaciones</p>
        </div>
      </div>
    </div>

    <!-- Info Card -->
    <Card class="info-card">
      <template #content>
        <div class="info-content">
          <div class="info-icon">
            <i class="pi pi-info-circle"></i>
          </div>
          <div class="info-text">
            <h3>¿Cómo funciona?</h3>
            <p>
              Agrega un chat personalizable a tu página web para que los usuarios puedan interactuar
              con tu asistente. El widget se adapta al diseño de tu sitio y es completamente
              configurable.
            </p>
          </div>
        </div>
      </template>
    </Card>

    <!-- Quick Setup Card -->
    <Card class="setup-card">
      <template #header>
        <div class="card-header">
          <div class="header-icon setup-header-icon">
            <i class="pi pi-cog"></i>
          </div>
          <div class="header-text">
            <h3>Configuración Rápida</h3>
            <p>Información esencial para comenzar</p>
          </div>
        </div>
      </template>
      <template #content>
        <div class="setup-content">
          <div class="setup-grid">
            <div class="setup-item">
              <div class="setup-label">
                <i class="pi pi-server"></i>
                Base URL
              </div>
              <div class="setup-value">
                <code>assistant.gillie.com.ar</code>
              </div>
            </div>

            <div class="setup-item">
              <div class="setup-label">
                <i class="pi pi-box"></i>
                Paquete NPM
              </div>
              <div class="setup-value">
                <a
                  href="https://www.npmjs.com/package/gillie-ai-assistant"
                  target="_blank"
                  class="npm-link"
                >
                  gillie-ai-assistant
                  <i class="pi pi-external-link"></i>
                </a>
              </div>
            </div>

            <div class="setup-item">
              <div class="setup-label">
                <i class="pi pi-key"></i>
                API Key
              </div>
              <div class="setup-value">
                <RouterLink to="/my-account" class="api-key-link">
                  Generar en Mi Cuenta
                  <i class="pi pi-arrow-right"></i>
                </RouterLink>
              </div>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Code Examples Grid -->
    <div class="code-grid">
      <!-- Configuration Card -->
      <Card class="code-card">
        <template #header>
          <div class="code-card-header">
            <div class="code-header-icon config-icon">
              <i class="pi pi-wrench"></i>
            </div>
            <div class="code-header-text">
              <h3>Configuración</h3>
              <p>Opciones completas del asistente</p>
            </div>
          </div>
        </template>
        <template #content>
          <div class="code-section">
            <div class="code-container">
              <div class="code-toolbar">
                <span class="code-title">Configuración del Asistente</span>
                <button
                  class="copy-button"
                  @click="copyToClipboard(codeConfig, 'Código de configuración')"
                  title="Copiar código"
                >
                  <i class="pi pi-copy"></i>
                  Copiar
                </button>
              </div>
              <div class="code-content">
                <pre class="language-javascript">
                  <code ref="codeConfigBlock" class="language-javascript" v-pre></code>
                </pre>
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Methods Card -->
      <Card class="code-card">
        <template #header>
          <div class="code-card-header">
            <div class="code-header-icon methods-icon">
              <i class="pi pi-code"></i>
            </div>
            <div class="code-header-text">
              <h3>Métodos</h3>
              <p>Control programático del asistente</p>
            </div>
          </div>
        </template>
        <template #content>
          <div class="code-section">
            <div class="code-container">
              <div class="code-toolbar">
                <span class="code-title">Métodos del Asistente</span>
                <button
                  class="copy-button"
                  @click="copyToClipboard(codeMethods, 'Código de métodos')"
                  title="Copiar código"
                >
                  <i class="pi pi-copy"></i>
                  Copiar
                </button>
              </div>
              <div class="code-content">
                <pre class="language-javascript">
                  <code class="language-javascript" ref="codeMethodsBlock" v-pre></code>
                </pre>
              </div>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Toast for Notifications -->
    <Toast position="top-right" />
  </div>
</template>

<style scoped>
.integration-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
  background: var(--do-bg);
}

/* Header Section */
.header-section {
  margin-bottom: 2rem;
}

.integration-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: var(--do-blue);
  flex-shrink: 0;
}

.web-icon {
  color: #2F82FF;
}

.header-content {
  flex: 1;
}

.integration-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
  color: var(--do-text);
}

.integration-subtitle {
  font-size: 1.125rem;
  color: var(--do-text-muted);
  margin: 0;
  font-weight: 400;
}

/* Info Card */
.info-card {
  margin-bottom: 2rem;
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
  background: rgba(59,130,246,0.08);
}

:deep(.info-card .p-card-content) {
  padding: 1.5rem 2rem;
}

.info-content {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.info-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.75rem;
  background: var(--color-info);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.25rem;
  flex-shrink: 0;
}

.info-text h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-info-dark);
}

.info-text p {
  margin: 0;
  color: var(--color-info-dark);
  line-height: 1.6;
}

/* Setup Card */
.setup-card {
  margin-bottom: 2rem;
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.setup-card:hover {
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

:deep(.setup-card .p-card-header) {
  background: rgba(16,185,129,0.08);
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e2e8f0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: var(--do-blue);
  flex-shrink: 0;
}

.setup-header-icon {
  color: var(--do-success);
}

.header-text h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #374151;
}

.header-text p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--do-text-muted);
}

:deep(.setup-card .p-card-content) {
  padding: 2rem;
}

.setup-grid {
  display: grid;
  gap: 1.5rem;
}

.setup-item {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1.5rem;
  background: rgba(255,255,255,0.04);
  border-radius: 0.75rem;
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.setup-item:hover {
  background: rgba(255,255,255,0.07);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.setup-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--do-text-muted);
}

.setup-label i {
  color: var(--color-info);
}

.setup-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.setup-value code {
  background: rgba(255,255,255,0.06);
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #e2e8f0;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.875rem;
  color: #374151;
}

.npm-link,
.api-key-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: rgba(255,255,255,0.04);
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  text-decoration: none;
  color: var(--color-info);
  font-weight: 500;
  font-size: 0.875rem;
  transition: all 0.3s ease;
}

.npm-link:hover,
.api-key-link:hover {
  background: var(--color-info);
  color: white;
  transform: translateY(-1px);
  box-shadow: var(--shadow-info);
}

/* Code Grid */
.code-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

/* Code Cards */
.code-card {
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.code-card:hover {
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

:deep(.code-card .p-card-header) {
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e2e8f0;
}

.code-card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.code-header-icon {
  color: var(--do-blue);
}

.config-icon {
  color: var(--do-blue);
}

.methods-icon {
  color: var(--do-blue);
}

.code-header-text h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #374151;
}

.code-header-text p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--do-text-muted);
}

:deep(.code-card .p-card-content) {
  padding: 0;
}

.code-section {
  width: 100%;
}

.code-container {
  width: 100%;
  background: #1e293b;
  border-radius: 0;
  overflow: hidden;
}

.code-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: #334155;
  border-bottom: 1px solid #475569;
}

.code-title {
  font-weight: 600;
  color: #e2e8f0;
  font-size: 0.875rem;
}

.copy-button {
  background: var(--gradient-info);
  color: white;
  border: none;
  border-radius: 0.5rem;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.copy-button:hover {
  background: linear-gradient(135deg, #0891b2 0%, #0e7490 100%);
  transform: translateY(-1px);
  box-shadow: var(--shadow-info);
}

.code-content {
  overflow-x: auto;
}

pre {
  margin: 0;
  padding: 1.5rem;
  background: #1e293b;
  color: #e2e8f0;
  overflow-x: auto;
}

code {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  color: #e2e8f0;
}

/* Responsive Design */
@media (max-width: 768px) {
  .integration-container {
    padding: 1rem;
  }

  .integration-header {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .integration-title {
    font-size: 2rem;
  }

  .integration-subtitle {
    font-size: 1rem;
  }

  .code-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .card-header,
  .code-card-header {
    padding: 1rem 1.5rem;
  }

  :deep(.setup-card .p-card-content),
  :deep(.info-card .p-card-content) {
    padding: 1.5rem;
  }

  :deep(.setup-card .p-card-header) {
    padding: 1rem 1.5rem;
  }

  .info-content {
    flex-direction: column;
    text-align: center;
  }

  .code-toolbar {
    padding: 0.75rem 1rem;
    flex-direction: column;
    gap: 0.75rem;
    align-items: stretch;
  }

  .copy-button {
    align-self: center;
  }

  pre {
    padding: 1rem;
  }

  code {
    font-size: 0.75rem;
  }
}

@media (max-width: 480px) {
  .integration-container {
    padding: 0.5rem;
  }

  .icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: var(--do-blue);
  flex-shrink: 0;
}

  .integration-title {
    font-size: 1.75rem;
  }

  .header-icon,
  .code-header-icon {
  color: var(--do-blue);
}

  :deep(.setup-card .p-card-content),
  :deep(.info-card .p-card-content) {
    padding: 1rem;
  }

  :deep(.setup-card .p-card-header) {
    padding: 1rem;
  }

  .setup-item {
    padding: 1rem;
  }

  .code-toolbar {
    padding: 0.5rem 0.75rem;
  }

  pre {
    padding: 0.75rem;
  }

  code {
    font-size: 0.7rem;
  }
}
</style>
