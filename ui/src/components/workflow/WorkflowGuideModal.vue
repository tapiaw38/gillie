<script setup lang="ts">
import { ref } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'

interface Props {
  visible: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const activeStep = ref(0)
const totalSteps = 4

const closeModal = () => {
  emit('update:visible', false)
  activeStep.value = 0
}

const nextStep = () => {
  if (activeStep.value < totalSteps - 1) {
    activeStep.value++
  }
}

const prevStep = () => {
  if (activeStep.value > 0) {
    activeStep.value--
  }
}

const jsonExample = `[
  {
    "type": "workflow",
    "name": "reserva_habitacion",
    "description": "Reserva de habitación completa",
    "input_params": ["guest_name", "email", "check_in"],
    "keywords": ["reserva", "hotel", "booking"],
    "steps": [
      {
        "name": "crear_reserva",
        "url": "localhost:8085/api/bookings",
        "method": "POST",
        "required_params": ["guest_name", "email"],
        "body_template": "{\\"name\\": \\"{guest_name}\\"}"
      }
    ]
  }
]`
</script>

<template>
  <Dialog
    :visible="props.visible"
    modal
    :closable="true"
    :draggable="false"
    class="guide-dialog"
    @update:visible="emit('update:visible', $event)"
  >
    <template #header>
      <div class="dialog-header">
        <i class="pi pi-book"></i>
        <h2>Guía Rápida de Workflows</h2>
      </div>
    </template>

    <div class="guide-content">
      <!-- Progress Indicator -->
      <div class="progress-steps">
        <div
          v-for="step in totalSteps"
          :key="step"
          class="progress-step"
          :class="{ active: activeStep === step - 1, completed: activeStep > step - 1 }"
        >
          <div class="step-circle">
            <i v-if="activeStep > step - 1" class="pi pi-check"></i>
            <span v-else>{{ step }}</span>
          </div>
          <div class="step-label">
            {{
              step === 1
                ? 'Introducción'
                : step === 2
                  ? 'JSON'
                  : step === 3
                    ? 'Visual'
                    : 'Consejos'
            }}
          </div>
        </div>
      </div>

      <!-- Step 1: Introduction -->
      <div v-if="activeStep === 0" class="step-content">
        <div class="step-icon intro">
          <i class="pi pi-info-circle"></i>
        </div>
        <h3>¿Qué son los Workflows?</h3>
        <p>
          Los workflows te permiten crear procesos automatizados con múltiples pasos que se
          ejecutan secuencialmente.
        </p>

        <div class="features-grid">
          <div class="feature-item">
            <i class="pi pi-bolt"></i>
            <div>
              <h4>Pasos Secuenciales</h4>
              <p>Ejecuta acciones en orden</p>
            </div>
          </div>
          <div class="feature-item">
            <i class="pi pi-sitemap"></i>
            <div>
              <h4>Lógica Condicional</h4>
              <p>Flujos según condiciones</p>
            </div>
          </div>
          <div class="feature-item">
            <i class="pi pi-globe"></i>
            <div>
              <h4>Integración API</h4>
              <p>Conecta con servicios externos</p>
            </div>
          </div>
          <div class="feature-item">
            <i class="pi pi-code"></i>
            <div>
              <h4>JSON o Visual</h4>
              <p>Configura como prefieras</p>
            </div>
          </div>
        </div>

        <div class="step-actions">
          <Button label="Siguiente" icon="pi pi-arrow-right" @click="nextStep" />
        </div>
      </div>

      <!-- Step 2: JSON Configuration -->
      <div v-if="activeStep === 1" class="step-content">
        <div class="step-icon json">
          <i class="pi pi-code"></i>
        </div>
        <h3>Configurar con JSON</h3>

        <div class="config-steps">
          <div class="config-step">
            <span class="step-number">1</span>
            <div class="step-info">
              <h4>Click en "Editar"</h4>
              <p>Activa el modo de edición del JSON</p>
            </div>
          </div>

          <div class="config-step">
            <span class="step-number">2</span>
            <div class="step-info">
              <h4>Escribe tu workflow</h4>
              <p>Define steps, métodos HTTP y parámetros</p>
            </div>
          </div>

          <div class="config-step">
            <span class="step-number">3</span>
            <div class="step-info">
              <h4>Guarda los cambios</h4>
              <p>Click en "Guardar Funciones"</p>
            </div>
          </div>
        </div>

        <div class="code-example">
          <div class="code-header">
            <i class="pi pi-file-edit"></i>
            <span>Ejemplo de workflow</span>
          </div>
          <pre class="code-block">{{ jsonExample }}</pre>
        </div>

        <div class="step-actions">
          <Button
            label="Anterior"
            severity="secondary"
            icon="pi pi-arrow-left"
            @click="prevStep"
          />
          <Button label="Siguiente" icon="pi pi-arrow-right" @click="nextStep" />
        </div>
      </div>

      <!-- Step 3: Visual Configuration -->
      <div v-if="activeStep === 2" class="step-content">
        <div class="step-icon visual">
          <i class="pi pi-sitemap"></i>
        </div>
        <h3>Configurar Visualmente</h3>

        <div class="config-steps">
          <div class="config-step">
            <span class="step-number">1</span>
            <div class="step-info">
              <h4>Click en "Editar"</h4>
              <p>Activa el modo de edición</p>
            </div>
          </div>

          <div class="config-step">
            <span class="step-number">2</span>
            <div class="step-info">
              <h4>Click en "Editor Visual"</h4>
              <p>Cambia al modo visual interactivo</p>
            </div>
          </div>

          <div class="config-step">
            <span class="step-number">3</span>
            <div class="step-info">
              <h4>Agrega nodos</h4>
              <p>Usa botones "Agregar HTTP" o "Agregar Condición"</p>
            </div>
          </div>

          <div class="config-step">
            <span class="step-number">4</span>
            <div class="step-info">
              <h4>Configura cada nodo</h4>
              <p>Click en un nodo para editar URL, método, parámetros</p>
            </div>
          </div>

          <div class="config-step">
            <span class="step-number">5</span>
            <div class="step-info">
              <h4>Conecta los nodos</h4>
              <p>Arrastra desde un punto de conexión a otro</p>
            </div>
          </div>

          <div class="config-step">
            <span class="step-number">6</span>
            <div class="step-info">
              <h4>Guarda el workflow</h4>
              <p>Click en "Guardar Workflow"</p>
            </div>
          </div>
        </div>

        <div class="tip-box">
          <i class="pi pi-lightbulb"></i>
          <div>
            <strong>Tip:</strong> Puedes arrastrar los nodos para reorganizarlos incluso en
            modo lectura.
          </div>
        </div>

        <div class="step-actions">
          <Button
            label="Anterior"
            severity="secondary"
            icon="pi pi-arrow-left"
            @click="prevStep"
          />
          <Button label="Siguiente" icon="pi pi-arrow-right" @click="nextStep" />
        </div>
      </div>

      <!-- Step 4: Tips & Best Practices -->
      <div v-if="activeStep === 3" class="step-content">
        <div class="step-icon tips">
          <i class="pi pi-star"></i>
        </div>
        <h3>Consejos y Buenas Prácticas</h3>

        <div class="tips-list">
          <div class="tip-item">
            <i class="pi pi-check-circle"></i>
            <div>
              <h4>Usa nombres descriptivos</h4>
              <p>Nombra tus pasos de forma clara: "validar_cliente", "crear_reserva"</p>
            </div>
          </div>

          <div class="tip-item">
            <i class="pi pi-check-circle"></i>
            <div>
              <h4>Mapea las respuestas</h4>
              <p>
                Usa response_mapping para extraer datos: {"is_valid": "data.valid"}
              </p>
            </div>
          </div>

          <div class="tip-item">
            <i class="pi pi-check-circle"></i>
            <div>
              <h4>Agrega condiciones</h4>
              <p>Controla el flujo con condiciones: "is_valid == true"</p>
            </div>
          </div>

          <div class="tip-item">
            <i class="pi pi-check-circle"></i>
            <div>
              <h4>Usa keywords relevantes</h4>
              <p>Ayuda al asistente a identificar cuándo usar tu workflow</p>
            </div>
          </div>

          <div class="tip-item">
            <i class="pi pi-check-circle"></i>
            <div>
              <h4>Alterna entre modos</h4>
              <p>Usa JSON para editar rápido y Visual para visualizar el flujo</p>
            </div>
          </div>
        </div>

        <div class="step-actions">
          <Button
            label="Anterior"
            severity="secondary"
            icon="pi pi-arrow-left"
            @click="prevStep"
          />
          <Button label="Finalizar" icon="pi pi-check" @click="closeModal" />
        </div>
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
:deep(.guide-dialog) {
  width: 760px;
  max-width: 760px;
}

:deep(.guide-dialog .p-dialog-header) {
  background: var(--gradient-primary);
  color: white;
  padding: 1.5rem 2rem;
}

:deep(.guide-dialog .p-dialog-content) {
  padding: 2rem;
}

.dialog-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.dialog-header i {
  font-size: 1.5rem;
}

.dialog-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.guide-content {
  min-height: 500px;
}

/* Progress Steps */
.progress-steps {
  display: flex;
  justify-content: center;
  gap: 2rem;
  margin-bottom: 2rem;
  padding: 1rem;
}

.progress-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.step-circle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  background: #e2e8f0;
  color: #64748b;
  transition: all 0.3s ease;
}

.progress-step.active .step-circle {
  background: var(--gradient-primary);
  color: white;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
  transform: scale(1.1);
}

.progress-step.completed .step-circle {
  background: var(--gradient-success);
  color: white;
}

.step-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #64748b;
}

.progress-step.active .step-label {
  color: var(--color-primary);
  font-weight: 600;
}

/* Step Content */
.step-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  padding: 1rem 0;
}

.step-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: white;
  margin: 0 auto;
}

.step-icon.intro {
  background: var(--gradient-info);
}

.step-icon.json {
  background: var(--gradient-success);
}

.step-icon.visual {
  background: var(--gradient-primary);
}

.step-icon.tips {
  background: var(--gradient-warning);
}

.step-content h3 {
  text-align: center;
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.step-content p {
  text-align: center;
  color: #64748b;
  font-size: 1rem;
  line-height: 1.6;
}

/* Features Grid */
.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  margin-top: 1rem;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 0.75rem;
  border: 1px solid #e2e8f0;
}

.feature-item i {
  font-size: 1.5rem;
  color: var(--color-primary);
  flex-shrink: 0;
}

.feature-item h4 {
  margin: 0 0 0.25rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #1e293b;
}

.feature-item p {
  margin: 0;
  font-size: 0.75rem;
  color: #64748b;
  text-align: left;
}

/* Config Steps */
.config-steps {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.config-step {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 0.75rem;
  border: 1px solid #e2e8f0;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--gradient-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.step-info h4 {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
}

.step-info p {
  margin: 0;
  font-size: 0.875rem;
  color: #64748b;
  text-align: left;
}

/* Code Example */
.code-example {
  border-radius: 0.75rem;
  overflow: hidden;
  border: 1px solid #e2e8f0;
}

.code-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: #1e293b;
  color: white;
  font-size: 0.875rem;
  font-weight: 500;
}

.code-block {
  margin: 0;
  padding: 1rem;
  background: #1e293b;
  color: #e2e8f0;
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 0.75rem;
  line-height: 1.5;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
}

/* Tip Box */
.tip-box {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #fef3c7;
  border: 1px solid #fbbf24;
  border-radius: 0.75rem;
}

.tip-box i {
  font-size: 1.5rem;
  color: var(--color-warning);
  flex-shrink: 0;
}

.tip-box strong {
  color: #92400e;
}

/* Tips List */
.tips-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.tip-item {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  background: #f0fdf4;
  border-radius: 0.75rem;
  border: 1px solid #86efac;
}

.tip-item i {
  font-size: 1.25rem;
  color: var(--color-success);
  flex-shrink: 0;
  margin-top: 0.25rem;
}

.tip-item h4 {
  margin: 0 0 0.25rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #065f46;
}

.tip-item p {
  margin: 0;
  font-size: 0.875rem;
  color: #047857;
  text-align: left;
}

/* Step Actions */
.step-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

/* Responsive */
@media (max-width: 768px) {
  :deep(.guide-dialog) {
    width: 100%;
    max-width: 100%;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .step-content {
    padding: 0.5rem 0;
  }

  .progress-steps {
    flex-direction: column;
    gap: 1rem;
  }

  .progress-step {
    flex-direction: row;
    justify-content: flex-start;
    gap: 1rem;
  }
}
</style>
