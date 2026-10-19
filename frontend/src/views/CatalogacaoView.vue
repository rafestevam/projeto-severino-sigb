<template>
  <div class="catalogacao-view">
    <h1 class="page-title">Catalogação</h1>

    <!-- Busca de ISBN -->
    <section class="card">
      <h2 class="section-title">Buscar por ISBN (opcional)</h2>
      <div class="form-row scanner-row">
        <label class="label-bip">ISBN (bipe ou digite)</label>
        <div class="input-and-button">
          <input
            ref="isbnInputRef"
            v-model="isbn"
            type="text"
            placeholder="ISBN (bipe ou digite)"
            class="cds--text-input isbn-input"
            :disabled="store.loading"
          />
          <cds-button
            kind="primary"
            size="md"
            :disabled="store.loading || !isbn.trim()"
            @click="handleBuscarIsbn"
            class="btn-buscar"
          >
            {{ store.loading ? 'Buscando…' : 'Buscar' }}
          </cds-button>
        </div>
      </div>
      <p v-if="store.erro" class="msg-erro">{{ store.erro }}</p>
    </section>

    <!-- Formulário de metadados -->
    <section class="card">
      <h2 class="section-title">Dados da Obra</h2>
      <div class="cds--grid cds--grid--narrow grid-container">
        <div class="cds--row">
          <!-- Título -->
          <div class="cds--col-sm-4 cds--col-md-8 cds--col-lg-8 field-wrapper">
            <cds-text-input
              label="Título *"
              placeholder="Título da obra"
              :value="store.metadados.titulo || ''"
              @input="store.metadados.titulo = ($event.target as any).value"
            ></cds-text-input>
          </div>
          <!-- Editora -->
          <div class="cds--col-sm-4 cds--col-md-8 cds--col-lg-8 field-wrapper">
            <cds-text-input
              label="Editora *"
              placeholder="Editora"
              :value="store.metadados.editora || ''"
              @input="store.metadados.editora = ($event.target as any).value"
            ></cds-text-input>
          </div>
          <!-- Ano -->
          <div class="cds--col-sm-4 cds--col-md-8 cds--col-lg-8 field-wrapper">
            <cds-text-input
              type="number"
              label="Ano *"
              placeholder="Ano"
              :value="store.metadados.ano || ''"
              @input="store.metadados.ano = ($event.target as any).value ? Number(($event.target as any).value) : null"
            ></cds-text-input>
          </div>
          <!-- Categoria -->
          <div class="cds--col-sm-4 cds--col-md-8 cds--col-lg-8 field-wrapper">
            <cds-text-input
              label="Categoria *"
              placeholder="Categoria"
              :value="store.metadados.categoria || ''"
              @input="store.metadados.categoria = ($event.target as any).value"
            ></cds-text-input>
          </div>
          <!-- Autores -->
          <div class="cds--col-sm-4 cds--col-md-8 cds--col-lg-16 field-wrapper">
            <cds-text-input
              label="Autores *"
              placeholder="Autores (separados por vírgula)"
              :value="store.metadados.autores?.join(', ') ?? ''"
              @input="handleAutoresInput"
            ></cds-text-input>
          </div>
          <!-- URL da Capa -->
          <div class="cds--col-sm-4 cds--col-md-8 cds--col-lg-16 field-wrapper">
            <cds-text-input
              type="url"
              label="URL da Capa"
              placeholder="https://..."
              :value="store.metadados.capa_url || ''"
              @input="store.metadados.capa_url = ($event.target as any).value"
            ></cds-text-input>
          </div>
          <!-- Sinopse (exibida no catálogo público) -->
          <div class="cds--col-sm-4 cds--col-md-8 cds--col-lg-16 field-wrapper">
            <cds-textarea
              label="Sinopse"
              helper-text="Exibida na página da obra no catálogo público."
              rows="4"
              :value="store.metadados.sinopse || ''"
              @input="store.metadados.sinopse = ($event.target as any).value"
            ></cds-textarea>
          </div>
        </div>
      </div>
    </section>

    <!-- Quantidade de exemplares e ações -->
    <section class="card card-acao">
      <div class="actions-row">
        <cds-text-input
          type="number"
          min="1"
          label="Quantidade de exemplares"
          :value="store.quantidadeExemplares"
          @input="store.quantidadeExemplares = Number(($event.target as any).value)"
          class="quantidade-input"
        ></cds-text-input>
        <div class="buttons-group">
          <cds-button
            kind="primary"
            :disabled="store.loading || !store.metadados.titulo"
            @click="store.salvar()"
          >
            {{ store.loading ? 'Salvando…' : 'Salvar' }}
          </cds-button>
          <cds-button
            kind="tertiary"
            :disabled="!store.etiquetaUrl"
            @click="store.imprimirEtiquetas()"
          >
            Imprimir Etiquetas
          </cds-button>
          <cds-button kind="secondary" @click="handleResetar">
            Novo Cadastro
          </cds-button>
        </div>
      </div>

      <div v-if="store.obraCriada" class="resultado">
        <cds-tag type="green">✓ Obra cadastrada</cds-tag>
        <strong class="resultado-nome">{{ store.obraCriada.titulo }}</strong>
        <cds-tag type="blue">{{ store.exemplaresCriados.length }} exemplar(es) criado(s)</cds-tag>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useCatalogacaoStore } from '@/stores/catalogacao'
import { useQrScanner } from '@/composables/useQrScanner'
import '@carbon/web-components/es/components/button/index.js'
import '@carbon/web-components/es/components/text-input/index.js'
import '@carbon/web-components/es/components/textarea/index.js'
import '@carbon/web-components/es/components/tag/index.js'

const store = useCatalogacaoStore()
const isbn = ref('')
const isbnInputRef = ref<HTMLInputElement | null>(null)

function handleBuscarIsbn() {
  if (isbn.value.trim()) {
    store.buscarIsbn(isbn.value.trim())
  }
}

function handleAutoresInput(event: Event) {
  const value = (event.target as HTMLInputElement).value
  store.metadados.autores = value.split(',').map((a) => a.trim()).filter(Boolean)
}

function handleResetar() {
  store.resetar()
  isbn.value = ''
}

const { attach, detach } = useQrScanner(isbnInputRef, (codigo) => {
  isbn.value = codigo
  store.buscarIsbn(codigo)
})

onMounted(() => {
  attach()
})

onUnmounted(() => {
  detach()
})
</script>

<style scoped lang="scss">
@use '@carbon/styles/scss/spacing' as *;
@use '@carbon/styles/scss/type' as type;

.catalogacao-view {
  max-width: 800px;
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

.input-and-button {
  display: flex;
  gap: $spacing-05;
  width: 100%;
}

.isbn-input {
  flex: 1;
  padding: $spacing-05;
  @include type.type-style('productive-heading-01');
  border: 2px solid var(--cds-focus, #0f62fe);
}

.btn-buscar {
  height: 40px;
}

.grid-container {
  padding: 0;
}

.field-wrapper {
  margin-bottom: $spacing-05;
}

.actions-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: $spacing-05;
  flex-wrap: wrap;
}

.quantidade-input {
  width: 180px;
}

.buttons-group {
  display: flex;
  gap: $spacing-04;
  align-items: center;
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
