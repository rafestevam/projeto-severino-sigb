<template>
  <div class="checkin-view">
    <h1 class="page-title">Check-In — Devolução</h1>
    <p class="subtitle">Bipe o livro para registrar a devolução automaticamente.</p>

    <!-- Campo único de QR com autofocus persistente -->
    <div class="scan-area">
      <input
        ref="qrInputRef"
        type="text"
        placeholder="Aponte o leitor de QR aqui…"
        class="cds--text-input qr-input"
        :disabled="store.loading"
        aria-label="Campo de leitura QR para devolução"
      />
      <span v-if="store.loading" class="loading-badge">Processando…</span>
    </div>

    <!-- Feedback de sucesso -->
    <div v-if="store.ultimaDevolucao" class="feedback feedback-sucesso">
      <div class="feedback-icon">✓</div>
      <div class="feedback-body">
        <p class="feedback-titulo">Devolução registrada com sucesso</p>
        <p class="feedback-detalhe">
          Exemplar: <strong>{{ store.ultimaDevolucao.exemplar_id }}</strong>
        </p>
        <p class="feedback-detalhe">
          Leitor: <strong>{{ store.ultimaDevolucao.leitor_id }}</strong>
        </p>
      </div>
    </div>

    <!-- Feedback de erro -->
    <div v-if="store.erro" class="feedback feedback-erro">
      <div class="feedback-icon">✗</div>
      <div class="feedback-body">
        <p class="feedback-titulo">Erro na devolução</p>
        <p class="feedback-detalhe">{{ store.erro }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useCheckinStore } from '@/stores/checkin'
import { useQrScanner } from '@/composables/useQrScanner'

const store = useCheckinStore()
const qrInputRef = ref<HTMLInputElement | null>(null)

const { attach, detach } = useQrScanner(qrInputRef, async (codigo) => {
  await store.devolverPorQr(codigo)
  // Reatribui o foco após processamento (campo foi limpo pelo composable)
  qrInputRef.value?.focus()
})

onMounted(() => {
  store.resetar()
  attach()
})

onUnmounted(() => {
  detach()
})
</script>

<style scoped lang="scss">
@use '@carbon/styles/scss/spacing' as *;
@use '@carbon/styles/scss/type' as type;

.checkin-view {
  max-width: 700px;
}

.page-title {
  @include type.type-style('productive-heading-03');
  font-weight: type.font-weight('semibold');
  margin-bottom: $spacing-02;
  color: var(--cds-text-primary, #161616);
}

.subtitle {
  @include type.type-style('body-long-01');
  color: var(--cds-text-secondary, #525252);
  margin-bottom: $spacing-06;
}

.scan-area {
  display: flex;
  align-items: center;
  gap: $spacing-05;
  margin-bottom: $spacing-06;
}

.qr-input {
  flex: 1;
  padding: $spacing-05;
  @include type.type-style('productive-heading-01');
  border: 2px solid var(--cds-focus, #0f62fe);
  outline: none;
}

.loading-badge {
  @include type.type-style('body-long-01');
  color: var(--cds-text-secondary);
  font-style: italic;
}

.feedback {
  display: flex;
  gap: $spacing-05;
  align-items: flex-start;
  padding: $spacing-05 $spacing-06;
  border-radius: 4px;
  margin-bottom: $spacing-05;
}

.feedback-sucesso {
  background: var(--cds-notification-success-background, #def8e9);
  border: 2px solid var(--cds-support-success, #24a148);
}

.feedback-erro {
  background: var(--cds-notification-error-background, #fff0f0);
  border: 2px solid var(--cds-support-error, #da1e28);
}

.feedback-icon {
  @include type.type-style('productive-heading-06');
  font-weight: type.font-weight('semibold');
  line-height: 1;
}

.feedback-sucesso .feedback-icon {
  color: var(--cds-support-success, #24a148);
}

.feedback-erro .feedback-icon {
  color: var(--cds-support-error, #da1e28);
}

.feedback-titulo {
  @include type.type-style('productive-heading-02');
  font-weight: type.font-weight('semibold');
  margin-bottom: $spacing-03;
}

.feedback-sucesso .feedback-titulo {
  color: var(--cds-support-success, #24a148);
}

.feedback-erro .feedback-titulo {
  color: var(--cds-support-error, #da1e28);
}

.feedback-detalhe {
  @include type.type-style('body-long-01');
  color: var(--cds-text-primary, #161616);
  margin: $spacing-01 0;
}
</style>
