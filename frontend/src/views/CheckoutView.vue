<template>
  <div class="checkout-view">
    <h1 class="page-title">Check-Out — Empréstimo</h1>

    <!-- Seção: busca de leitor por CPF -->
    <section class="card">
      <h2 class="section-title">1. Identificar Leitor</h2>
      <div class="form-row">
        <cds-text-input
          class="cpf-input"
          :value="cpf"
          @input="cpf = ($event.target as any).value"
          label-text="CPF do leitor"
          placeholder="CPF (somente números)"
          @keydown.enter="handleBuscarLeitor"
          :disabled="store.loading"
        ></cds-text-input>
        <cds-button
          kind="primary"
          size="md"
          @click="handleBuscarLeitor"
          :disabled="store.loading"
          class="btn-buscar"
        >
          Buscar
        </cds-button>
      </div>
      <p v-if="store.erroLeitor" class="msg-erro">{{ store.erroLeitor }}</p>
      <div v-if="store.leitor" class="resultado">
        <cds-tag type="green">✓ Leitor identificado</cds-tag>
        <strong class="resultado-nome">{{ store.leitor.nome }}</strong>
        <cds-tag v-if="!store.leitor.ativo" type="warm-gray">Inativo</cds-tag>
      </div>
    </section>

    <!-- Seção: leitura do exemplar -->
    <section class="card">
      <h2 class="section-title">2. Bipar Exemplar</h2>
      <div class="form-row scanner-row">
        <label class="label-bip">Código QR (aponte o leitor aqui)</label>
        <input
          ref="qrInputRef"
          type="text"
          placeholder="Código QR"
          class="cds--text-input qr-input"
          :disabled="store.loading || !store.leitor"
        />
      </div>
      <p v-if="store.erroExemplar" class="msg-erro">{{ store.erroExemplar }}</p>
      <div v-if="store.exemplar" class="resultado">
        <cds-tag type="green">✓ Exemplar identificado</cds-tag>
        <strong class="resultado-nome">{{ store.exemplar.titulo_obra ?? store.exemplar.codigo_qr }}</strong>
        <cds-tag type="blue">{{ store.exemplar.estado }}</cds-tag>
      </div>
    </section>

    <!-- Seção: confirmação -->
    <section class="card card-acao">
      <p v-if="store.erroCheckout" class="msg-erro">{{ store.erroCheckout }}</p>
      <div class="form-row">
        <cds-button
          kind="primary"
          size="lg"
          :disabled="!store.leitor || !store.exemplar || store.loading"
          @click="store.confirmarCheckout()"
        >
          {{ store.loading ? 'Processando…' : 'Confirmar Empréstimo' }}
        </cds-button>
        <cds-button kind="secondary" size="lg" @click="store.resetar()">
          Limpar
        </cds-button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useCheckoutStore } from '@/stores/checkout'
import { useQrScanner } from '@/composables/useQrScanner'
import '@carbon/web-components/es/components/button/index.js'
import '@carbon/web-components/es/components/text-input/index.js'
import '@carbon/web-components/es/components/tag/index.js'

const store = useCheckoutStore()
const { leitor } = storeToRefs(store)

const cpf = ref('')
const qrInputRef = ref<HTMLInputElement | null>(null)

const { attach, detach } = useQrScanner(qrInputRef, (codigo) => {
  store.buscarExemplar(codigo)
})

function handleBuscarLeitor() {
  if (cpf.value.trim()) {
    store.buscarLeitor(cpf.value.trim())
  }
}

// Foca no campo QR quando o leitor for identificado
watch(leitor, (novoLeitor) => {
  if (novoLeitor) {
    attach()
  }
})

onMounted(() => {
  store.resetar()
})

onUnmounted(() => {
  detach()
})
</script>

<style scoped lang="scss">
@use '@carbon/styles/scss/spacing' as *;
@use '@carbon/styles/scss/type' as type;

.checkout-view {
  max-width: 700px;
}

.page-title {
  @include type.type-style('productive-heading-03');
  font-weight: type.font-weight('semibold');
  margin-bottom: $spacing-06;
  color: var(--cds-text-primary, #161616);
}

.card {
  background: var(--cds-layer-01, #f4f4f4);
  border: 1px solid var(--cds-border-subtle-01, #e0e0e0);
  padding: $spacing-05;
  margin-bottom: $spacing-05;
}

.section-title {
  @include type.type-style('productive-heading-02');
  font-weight: type.font-weight('semibold');
  margin-bottom: $spacing-05;
  color: var(--cds-text-secondary, #525252);
}

.card-acao {
  background: var(--cds-layer-02, #ffffff);
}

.form-row {
  display: flex;
  gap: $spacing-05;
  align-items: flex-end;
  flex-wrap: wrap;
}

.cpf-input {
  flex: 1;
  min-width: 200px;
}

.btn-buscar {
  height: 40px;
}

.scanner-row {
  flex-direction: column;
  align-items: flex-start;
  gap: $spacing-02;
}

.label-bip {
  @include type.type-style('label-01');
  font-weight: type.font-weight('semibold');
  color: var(--cds-text-secondary, #525252);
}

.qr-input {
  width: 100%;
  padding: $spacing-05;
  @include type.type-style('productive-heading-01');
  border: 2px solid var(--cds-focus, #0f62fe);
}

.resultado {
  display: flex;
  align-items: center;
  gap: $spacing-03;
  margin-top: $spacing-04;
}

.resultado-nome {
  @include type.type-style('body-long-01');
  font-weight: type.font-weight('semibold');
  color: var(--cds-text-primary, #161616);
}

.msg-erro {
  @include type.type-style('body-long-01');
  color: var(--cds-support-error, #da1e28);
  margin-top: $spacing-03;
}
</style>
