<template>
  <cds-modal open size="sm" @cds-modal-closed="$emit('cancelar')">
    <cds-modal-header>
      <cds-modal-close-button></cds-modal-close-button>
      <cds-modal-heading>Dar Baixa no Exemplar</cds-modal-heading>
    </cds-modal-header>
    <cds-modal-body>
      <p class="modal-desc">
        Exemplar: <strong>{{ codigoQr }}</strong>
      </p>
      <div class="form-field">
        <cds-text-input
          id="motivo-input"
          label-text="Motivo da baixa *"
          placeholder="Ex: extraviado, danificado…"
          :value="motivo"
          @input="motivo = ($event.target as any).value"
          @keydown.enter="handleConfirmar"
          data-modal-primary-focus
        ></cds-text-input>
      </div>
    </cds-modal-body>
    <cds-modal-footer>
      <cds-modal-footer-button kind="secondary" @click="$emit('cancelar')">
        Cancelar
      </cds-modal-footer-button>
      <cds-modal-footer-button
        kind="danger"
        :disabled="!motivo.trim()"
        @click="handleConfirmar"
      >
        Confirmar Baixa
      </cds-modal-footer-button>
    </cds-modal-footer>
  </cds-modal>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import '@carbon/web-components/es/components/modal/index.js'
import '@carbon/web-components/es/components/text-input/index.js'

defineProps<{
  codigoQr: string
}>()

const emit = defineEmits<{
  confirmar: [motivo: string]
  cancelar: []
}>()

const motivo = ref('')

function handleConfirmar() {
  if (motivo.value.trim()) {
    emit('confirmar', motivo.value.trim())
  }
}
</script>

<style scoped lang="scss">
@use '@carbon/styles/scss/spacing' as *;
@use '@carbon/styles/scss/type' as type;

.modal-desc {
  @include type.type-style('body-long-01');
  color: var(--cds-text-secondary);
  margin-bottom: $spacing-05;
}

.form-field {
  margin-bottom: $spacing-05;
}
</style>
