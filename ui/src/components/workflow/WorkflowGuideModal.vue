<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'

interface Props {
  visible: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const { t } = useI18n()
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
    "name": "room_booking",
    "description": "Complete room booking",
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
        <h2>{{ t('workflow.guide.title') }}</h2>
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
          <div class="stepper-track">
            <div class="step-circle">
              <i v-if="activeStep > step - 1" class="pi pi-check"></i>
              <span v-else>{{ step }}</span>
            </div>
            <div v-if="step < totalSteps" class="step-connector"></div>
          </div>
          <div class="step-label">
            {{
              step === 1
                ? t('workflow.guide.step1Label')
                : step === 2
                  ? t('workflow.guide.step2Label')
                  : step === 3
                    ? t('workflow.guide.step3Label')
                    : t('workflow.guide.step4Label')
            }}
          </div>
        </div>
      </div>

      <!-- Step 1: Introduction -->
      <div v-if="activeStep === 0" class="step-content">
        <div class="step-heading">
          <div class="step-icon intro">
            <i class="pi pi-info-circle"></i>
          </div>
          <h3>{{ t('workflow.guide.step1Title') }}</h3>
        </div>
        <p>{{ t('workflow.guide.step1Desc') }}</p>

        <div class="features-grid">
          <div class="feature-item">
            <i class="pi pi-bolt"></i>
            <div>
              <h4>{{ t('workflow.guide.feature1Title') }}</h4>
              <p>{{ t('workflow.guide.feature1Desc') }}</p>
            </div>
          </div>
          <div class="feature-item">
            <i class="pi pi-sitemap"></i>
            <div>
              <h4>{{ t('workflow.guide.feature2Title') }}</h4>
              <p>{{ t('workflow.guide.feature2Desc') }}</p>
            </div>
          </div>
          <div class="feature-item">
            <i class="pi pi-globe"></i>
            <div>
              <h4>{{ t('workflow.guide.feature3Title') }}</h4>
              <p>{{ t('workflow.guide.feature3Desc') }}</p>
            </div>
          </div>
          <div class="feature-item">
            <i class="pi pi-code"></i>
            <div>
              <h4>{{ t('workflow.guide.feature4Title') }}</h4>
              <p>{{ t('workflow.guide.feature4Desc') }}</p>
            </div>
          </div>
        </div>

        <div class="step-actions">
          <span></span>
          <Button :label="t('workflow.guide.next')" icon="pi pi-arrow-right" icon-pos="right" @click="nextStep" />
        </div>
      </div>

      <!-- Step 2: JSON Configuration -->
      <div v-if="activeStep === 1" class="step-content">
        <div class="step-heading">
          <div class="step-icon json">
            <i class="pi pi-code"></i>
          </div>
          <h3>{{ t('workflow.guide.step2Title') }}</h3>
        </div>

        <div class="step-two-col">
          <div class="config-steps">
            <div class="config-step">
              <span class="step-number">1</span>
              <div class="step-info">
                <h4>{{ t('workflow.guide.jsonStep1Title') }}</h4>
                <p>{{ t('workflow.guide.jsonStep1Desc') }}</p>
              </div>
            </div>

            <div class="config-step">
              <span class="step-number">2</span>
              <div class="step-info">
                <h4>{{ t('workflow.guide.jsonStep2Title') }}</h4>
                <p>{{ t('workflow.guide.jsonStep2Desc') }}</p>
              </div>
            </div>

            <div class="config-step">
              <span class="step-number">3</span>
              <div class="step-info">
                <h4>{{ t('workflow.guide.jsonStep3Title') }}</h4>
                <p>{{ t('workflow.guide.jsonStep3Desc') }}</p>
              </div>
            </div>
          </div>

          <div class="code-example">
            <div class="code-header">
              <i class="pi pi-file-edit"></i>
              <span>{{ t('workflow.guide.jsonExample') }}</span>
            </div>
            <pre class="code-block">{{ jsonExample }}</pre>
          </div>
        </div>

        <div class="step-actions">
          <Button
            :label="t('workflow.guide.prev')"
            severity="secondary"
            icon="pi pi-arrow-left"
            @click="prevStep"
          />
          <Button :label="t('workflow.guide.next')" icon="pi pi-arrow-right" icon-pos="right" @click="nextStep" />
        </div>
      </div>

      <!-- Step 3: Visual Configuration -->
      <div v-if="activeStep === 2" class="step-content">
        <div class="step-heading">
          <div class="step-icon visual">
            <i class="pi pi-sitemap"></i>
          </div>
          <h3>{{ t('workflow.guide.step3Title') }}</h3>
        </div>

        <div class="step-two-col">
          <div class="config-steps">
            <div class="config-step">
              <span class="step-number">1</span>
              <div class="step-info">
                <h4>{{ t('workflow.guide.visualStep1Title') }}</h4>
                <p>{{ t('workflow.guide.visualStep1Desc') }}</p>
              </div>
            </div>

            <div class="config-step">
              <span class="step-number">2</span>
              <div class="step-info">
                <h4>{{ t('workflow.guide.visualStep2Title') }}</h4>
                <p>{{ t('workflow.guide.visualStep2Desc') }}</p>
              </div>
            </div>

            <div class="config-step">
              <span class="step-number">3</span>
              <div class="step-info">
                <h4>{{ t('workflow.guide.visualStep3Title') }}</h4>
                <p>{{ t('workflow.guide.visualStep3Desc') }}</p>
              </div>
            </div>

            <div class="config-step">
              <span class="step-number">4</span>
              <div class="step-info">
                <h4>{{ t('workflow.guide.visualStep4Title') }}</h4>
                <p>{{ t('workflow.guide.visualStep4Desc') }}</p>
              </div>
            </div>

            <div class="config-step">
              <span class="step-number">5</span>
              <div class="step-info">
                <h4>{{ t('workflow.guide.visualStep5Title') }}</h4>
                <p>{{ t('workflow.guide.visualStep5Desc') }}</p>
              </div>
            </div>

            <div class="config-step">
              <span class="step-number">6</span>
              <div class="step-info">
                <h4>{{ t('workflow.guide.visualStep6Title') }}</h4>
                <p>{{ t('workflow.guide.visualStep6Desc') }}</p>
              </div>
            </div>
          </div>

          <div class="tip-box">
            <i class="pi pi-lightbulb"></i>
            <div>
              <strong>{{ t('workflow.guide.tip') }}:</strong> {{ t('workflow.guide.tipDesc') }}
            </div>
          </div>
        </div>

        <div class="step-actions">
          <Button
            :label="t('workflow.guide.prev')"
            severity="secondary"
            icon="pi pi-arrow-left"
            @click="prevStep"
          />
          <Button :label="t('workflow.guide.next')" icon="pi pi-arrow-right" icon-pos="right" @click="nextStep" />
        </div>
      </div>

      <!-- Step 4: Tips & Best Practices -->
      <div v-if="activeStep === 3" class="step-content">
        <div class="step-heading">
          <div class="step-icon tips">
            <i class="pi pi-star"></i>
          </div>
          <h3>{{ t('workflow.guide.step4Title') }}</h3>
        </div>

        <div class="tips-list">
          <div class="tip-item">
            <i class="pi pi-check-circle"></i>
            <div>
              <h4>{{ t('workflow.guide.tip1Title') }}</h4>
              <p>{{ t('workflow.guide.tip1Desc') }}</p>
            </div>
          </div>

          <div class="tip-item">
            <i class="pi pi-check-circle"></i>
            <div>
              <h4>{{ t('workflow.guide.tip2Title') }}</h4>
              <p>{{ t('workflow.guide.tip2Desc') }}</p>
            </div>
          </div>

          <div class="tip-item">
            <i class="pi pi-check-circle"></i>
            <div>
              <h4>{{ t('workflow.guide.tip3Title') }}</h4>
              <p>{{ t('workflow.guide.tip3Desc') }}</p>
            </div>
          </div>

          <div class="tip-item">
            <i class="pi pi-check-circle"></i>
            <div>
              <h4>{{ t('workflow.guide.tip4Title') }}</h4>
              <p>{{ t('workflow.guide.tip4Desc') }}</p>
            </div>
          </div>

          <div class="tip-item">
            <i class="pi pi-check-circle"></i>
            <div>
              <h4>{{ t('workflow.guide.tip5Title') }}</h4>
              <p>{{ t('workflow.guide.tip5Desc') }}</p>
            </div>
          </div>
        </div>

        <div class="step-actions">
          <Button
            :label="t('workflow.guide.prev')"
            severity="secondary"
            icon="pi pi-arrow-left"
            @click="prevStep"
          />
          <Button :label="t('workflow.guide.finish')" severity="success" icon="pi pi-check" @click="closeModal" />
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

:deep(.guide-dialog .p-dialog) {
  background: var(--do-bg);
}

:deep(.guide-dialog .p-dialog-header) {
  background: var(--gradient-primary);
  color: white;
  padding: 1.5rem 2rem;
}

:deep(.guide-dialog .p-dialog-content) {
  background: var(--do-bg);
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
  max-height: 80vh;
  overflow-y: auto;
}

/* Progress Steps — horizontal stepper with connecting lines */
.progress-steps {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  margin-bottom: 2rem;
  padding: 1rem 0;
}

.progress-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  max-width: 120px;
}

.stepper-track {
  display: flex;
  align-items: center;
  width: 100%;
}

.step-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
  background: rgba(255, 255, 255, 0.08);
  color: var(--do-text-muted);
  transition: all 0.3s ease;
  flex-shrink: 0;
  border: 1px solid var(--do-border-light);
}

.step-connector {
  flex: 1;
  height: 1px;
  background: var(--do-border-light);
  margin: 0 4px;
  transition: background 0.3s ease;
}

.progress-step.active .step-circle {
  background: var(--gradient-primary);
  color: white;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
  transform: scale(1.1);
  border-color: transparent;
}

.progress-step.completed .step-circle {
  background: var(--gradient-success);
  color: white;
  border-color: transparent;
}

.progress-step.completed .step-connector {
  background: var(--color-success);
}

.step-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--do-text-muted);
  text-align: center;
  white-space: nowrap;
}

.progress-step.active .step-label {
  color: var(--color-primary);
  font-weight: 600;
}

.progress-step.completed .step-label {
  color: var(--color-success);
}

/* Step Content */
.step-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 0.5rem 0;
}

/* Step heading: icon + title inline */
.step-heading {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.step-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  color: white;
  flex-shrink: 0;
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
  font-size: 1.375rem;
  font-weight: 600;
  color: var(--do-text);
  margin: 0;
}

.step-content > p {
  color: var(--do-text-muted);
  font-size: 1rem;
  line-height: 1.6;
  margin: 0;
}

/* Features Grid */
.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 0.75rem;
  border: 1px solid var(--do-border-light);
  border-left: 3px solid var(--color-primary);
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
  color: var(--do-text);
}

.feature-item p {
  margin: 0;
  font-size: 0.75rem;
  color: var(--do-text-muted);
  text-align: left;
}

/* Two-column layout for steps 2 and 3 */
.step-two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  align-items: start;
}

/* Config Steps — vertical connected list */
.config-steps {
  display: flex;
  flex-direction: column;
  position: relative;
}

.config-steps::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 32px;
  bottom: 16px;
  width: 1px;
  background: var(--do-border-light);
  z-index: 0;
}

.config-step {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 0.75rem;
  border: 1px solid var(--do-border-light);
  position: relative;
  z-index: 1;
  margin-bottom: 0.5rem;
}

.config-step:last-child {
  margin-bottom: 0;
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
  font-size: 0.875rem;
  flex-shrink: 0;
  position: relative;
  z-index: 2;
}

.step-info h4 {
  margin: 0 0 0.25rem 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--do-text);
}

.step-info p {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--do-text-muted);
  text-align: left;
}

/* Code Example */
.code-example {
  border-radius: 0.75rem;
  overflow: hidden;
  border: 1px solid var(--do-border-light);
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
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  background: rgba(251, 191, 36, 0.12);
  border: 1px solid rgba(251, 191, 36, 0.35);
  border-radius: 0.75rem;
  color: var(--do-text);
}

.tip-box i {
  font-size: 1.5rem;
  color: var(--color-warning);
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.tip-box strong {
  color: var(--color-warning);
}

/* Tips List */
.tips-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.tip-item {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 0.875rem 1rem;
  background: rgba(34, 197, 94, 0.08);
  border-radius: 0.75rem;
  border: 1px solid rgba(34, 197, 94, 0.25);
}

.tip-item i {
  font-size: 1.25rem;
  color: var(--color-success);
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.tip-item h4 {
  margin: 0 0 0.25rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-success);
}

.tip-item p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--do-text-muted);
  text-align: left;
}

/* Step Actions — full-width, space-between */
.step-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--do-border-light);
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

  .step-two-col {
    grid-template-columns: 1fr;
  }

  .step-content {
    padding: 0.25rem 0;
  }

  .progress-steps {
    gap: 0;
  }

  .config-steps::before {
    display: none;
  }
}
</style>
