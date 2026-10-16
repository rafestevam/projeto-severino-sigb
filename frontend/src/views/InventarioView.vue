<template>
  <div class="inventario-view">
    <h1 class="page-title">Inventário</h1>

    <!-- Controles iniciais -->
    <section class="card" v-if="!store.scanAtivo && !store.divergencias">
      <div class="form-row">
        <cds-text-input
          class="localizacao-input"
          label-text="Localização"
          placeholder="Ex: Estante A-01"
          :value="localizacao"
          @input="localizacao = ($event.target as any).value"
        ></cds-text-input>
        <cds-button
          kind="primary"
          size="md"
          @click="handleIniciarScan"
          :disabled="!localizacao.trim()"
          class="btn-iniciar"
        >
          Iniciar Scan
        </cds-button>
      </div>
      <p v-if="store.erro" class="msg-erro">{{ store.erro }}</p>
    </section>

    <!-- Campo de bipagem contínua -->
    <section class="card" v-if="store.scanAtivo">
      <h2 class="scan-title">Bipagem contínua — {{ store.codigosBipados.length }} código(s) lidos</h2>
      <div class="form-row scanner-row">
        <label class="label-bip">Leitor QR</label>
        <input
          ref="qrInputRef"
          type="text"
          placeholder="Aponte o leitor de QR aqui…"
          class="cds--text-input qr-input"
        />
      </div>
      <ul class="codigo-list" v-if="store.codigosBipados.length > 0">
        <li v-for="codigo in store.codigosBipados" :key="codigo" class="codigo-item">
          {{ codigo }}
        </li>
      </ul>
      <div class="form-row btn-row">
        <cds-button
          kind="primary"
          :disabled="store.loading || store.codigosBipados.length === 0"
          @click="store.processar(localizacao)"
        >
          {{ store.loading ? 'Processando…' : 'Processar Inventário' }}
        </cds-button>
        <cds-button kind="secondary" @click="store.resetar()">
          Cancelar
        </cds-button>
      </div>
    </section>

    <!-- Resultados de divergências -->
    <template v-if="store.divergencias">
      <div class="form-row btn-row reset-row">
        <cds-button kind="secondary" @click="store.resetar()">Novo Inventário</cds-button>
      </div>

      <!-- Encontrados -->
      <section class="card">
        <h2 class="section-title section-ok">
          ✓ Encontrados ({{ store.divergencias.encontrados.length }})
        </h2>
        <p v-if="store.divergencias.encontrados.length === 0" class="vazio">Nenhum.</p>
        <ul class="codigo-list" v-else>
          <li v-for="c in store.divergencias.encontrados" :key="c" class="codigo-item">
            {{ c }}
          </li>
        </ul>
      </section>

      <!-- Não bipados -->
      <section class="card">
        <h2 class="section-title section-aviso">
          ⚠ Não bipados ({{ store.divergencias.nao_bipados.length }})
        </h2>
        <p v-if="store.divergencias.nao_bipados.length === 0" class="vazio">Nenhum.</p>
        <div v-else class="table-container">
          <table class="cds--data-table cds--data-table--compact">
            <thead>
              <tr>
                <th><span class="cds--table-header-label">Código QR</span></th>
                <th><span class="cds--table-header-label">Título</span></th>
                <th class="align-center"><span class="cds--table-header-label">Ação</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="exemplar in store.divergencias.nao_bipados" :key="exemplar.id">
                <td class="codigo-item-cell">{{ exemplar.codigo_qr }}</td>
                <td>{{ exemplar.titulo_obra ?? '—' }}</td>
                <td class="align-center">
                  <cds-button
                    kind="danger"
                    size="sm"
                    @click="abrirModalBaixa(exemplar.id, exemplar.codigo_qr)"
                  >
                    Dar Baixa
                  </cds-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Não esperados -->
      <section class="card">
        <h2 class="section-title section-erro">
          ✗ Não esperados ({{ store.divergencias.nao_esperados.length }})
        </h2>
        <p v-if="store.divergencias.nao_esperados.length === 0" class="vazio">Nenhum.</p>
        <ul class="codigo-list" v-else>
          <li v-for="c in store.divergencias.nao_esperados" :key="c" class="codigo-item codigo-erro">
            {{ c }}
          </li>
        </ul>
      </section>

      <p v-if="store.erro" class="msg-erro">{{ store.erro }}</p>
    </template>

    <!-- Modal de baixa -->
    <ModalBaixa
      v-if="modalBaixa.aberto"
      :codigo-qr="modalBaixa.codigoQr"
      @confirmar="handleDarBaixa"
      @cancelar="modalBaixa.aberto = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, reactive } from 'vue'
import { useQrScanner } from '@/composables/useQrScanner'
import { useInventarioStore } from '@/stores/inventario'
import ModalBaixa from '@/components/ModalBaixa.vue'
import '@carbon/web-components/es/components/button/index.js'
import '@carbon/web-components/es/components/text-input/index.js'

const store = useInventarioStore()
const localizacao = ref('')
const qrInputRef = ref<HTMLInputElement | null>(null)

const modalBaixa = reactive({
  aberto: false,
  exemplarId: '',
  codigoQr: '',
})

const { attach, detach } = useQrScanner(qrInputRef, (codigo) => {
  store.adicionarCodigo(codigo)
})

function handleIniciarScan() {
  store.iniciarScan()
  // O attach é chamado no próximo tick após o campo ser renderizado
  setTimeout(() => attach(), 50)
}

function abrirModalBaixa(exemplarId: string, codigoQr: string) {
  modalBaixa.exemplarId = exemplarId
  modalBaixa.codigoQr = codigoQr
  modalBaixa.aberto = true
}

async function handleDarBaixa(motivo: string) {
  modalBaixa.aberto = false
  await store.darBaixa(modalBaixa.exemplarId, motivo)
}

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

.inventario-view {
  max-width: 900px;
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

.scan-title {
  @include type.type-style('productive-heading-02');
  font-weight: type.font-weight('semibold');
  margin-bottom: $spacing-05;
  color: var(--cds-text-primary, #161616);
}

.section-title {
  @include type.type-style('productive-heading-02');
  font-weight: type.font-weight('semibold');
  margin-bottom: $spacing-05;
}

.section-ok {
  color: var(--cds-support-success, #24a148);
}

.section-aviso {
  color: var(--cds-support-warning, #f1c21b);
}

.section-erro {
  color: var(--cds-support-error, #da1e28);
}

.form-row {
  display: flex;
  gap: $spacing-05;
  align-items: flex-end;
  flex-wrap: wrap;
}

.localizacao-input {
  flex: 1;
  min-width: 250px;
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

.btn-iniciar {
  height: 40px;
}

.btn-row {
  margin-top: $spacing-05;
  gap: $spacing-04;
}

.reset-row {
  margin-bottom: $spacing-05;
}

.qr-input {
  width: 100%;
  padding: $spacing-05;
  @include type.type-style('productive-heading-01');
  border: 2px solid var(--cds-focus, #0f62fe);
}

.codigo-list {
  list-style: none;
  padding: 0;
  margin: $spacing-04 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-03;
}

.codigo-item {
  background: var(--cds-layer-selected-01, #e0e0e0);
  padding: $spacing-01 $spacing-03;
  @include type.type-style('label-01');
  font-family: type.font-family('mono');
  color: var(--cds-text-primary, #161616);
}

.codigo-erro {
  background: var(--cds-support-error-inverse, #ffb3b3);
  color: var(--cds-support-error, #da1e28);
}

.table-container {
  width: 100%;
  overflow-x: auto;
}

.codigo-item-cell {
  font-family: type.font-family('mono');
}

.align-center {
  text-align: center !important;
}

.vazio {
  @include type.type-style('body-long-01');
  color: var(--cds-text-placeholder, #a8a8a8);
}

.msg-erro {
  @include type.type-style('body-long-01');
  color: var(--cds-support-error, #da1e28);
  margin-top: $spacing-03;
}
</style>
