<template>
  <div class="catalogacao-view">
    <h1 class="page-title">Catalogação</h1>

    <!-- Busca de ISBN -->
    <section class="card">
      <h2>Buscar por ISBN (opcional)</h2>
      <div class="form-row">
        <input
          ref="isbnInputRef"
          v-model="isbn"
          type="text"
          placeholder="ISBN (bipe ou digite)"
          class="input"
          :disabled="store.loading"
        />
        <button
          class="btn btn-primary"
          :disabled="store.loading || !isbn.trim()"
          @click="handleBuscarIsbn"
        >
          {{ store.loading ? 'Buscando…' : 'Buscar' }}
        </button>
      </div>
      <p v-if="store.erro" class="msg-erro">{{ store.erro }}</p>
    </section>

    <!-- Formulário de metadados -->
    <section class="card">
      <h2>Dados da Obra</h2>
      <div class="form-grid">
        <div class="form-field">
          <label>Título *</label>
          <input v-model="store.metadados.titulo" type="text" class="input" placeholder="Título da obra" />
        </div>
        <div class="form-field">
          <label>Editora *</label>
          <input v-model="store.metadados.editora" type="text" class="input" placeholder="Editora" />
        </div>
        <div class="form-field">
          <label>Ano *</label>
          <input v-model.number="store.metadados.ano" type="number" class="input" placeholder="Ano" />
        </div>
        <div class="form-field">
          <label>Categoria *</label>
          <input v-model="store.metadados.categoria" type="text" class="input" placeholder="Categoria" />
        </div>
        <div class="form-field form-field-full">
          <label>Autores *</label>
          <input
            :value="store.metadados.autores?.join(', ') ?? ''"
            type="text"
            class="input"
            placeholder="Autores (separados por vírgula)"
            @input="handleAutoresInput"
          />
        </div>
        <div class="form-field form-field-full">
          <label>URL da Capa</label>
          <input v-model="store.metadados.capa_url" type="url" class="input" placeholder="https://..." />
        </div>
      </div>
    </section>

    <!-- Quantidade de exemplares e ações -->
    <section class="card card-acao">
      <div class="form-row">
        <label class="label-inline">Quantidade de exemplares:</label>
        <input
          v-model.number="store.quantidadeExemplares"
          type="number"
          min="1"
          class="input input-sm"
        />
        <button
          class="btn btn-success"
          :disabled="store.loading || !store.metadados.titulo"
          @click="store.salvar()"
        >
          {{ store.loading ? 'Salvando…' : 'Salvar' }}
        </button>
        <button
          class="btn btn-info"
          :disabled="!store.etiquetaUrl"
          @click="store.imprimirEtiquetas()"
        >
          Imprimir Etiquetas
        </button>
        <button class="btn btn-secondary" @click="handleResetar">
          Novo Cadastro
        </button>
      </div>

      <div v-if="store.obraCriada" class="resultado">
        <span class="tag tag-ok">✓ Obra cadastrada</span>
        <strong>{{ store.obraCriada.titulo }}</strong>
        <span class="tag tag-info">{{ store.exemplaresCriados.length }} exemplar(es) criado(s)</span>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useCatalogacaoStore } from '@/stores/catalogacao'
import { useQrScanner } from '@/composables/useQrScanner'

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

<style scoped>
.catalogacao-view {
  max-width: 800px;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  color: #1c1c1e;
}

.card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.25rem;
  margin-bottom: 1rem;
}

.card h2 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: #555;
}

.card-acao {
  background: #f0f4ff;
}

.form-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.form-field-full {
  grid-column: 1 / -1;
}

.form-field label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #555;
}

.input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.95rem;
}

.input-sm {
  width: 80px;
}

.label-inline {
  font-size: 0.9rem;
  font-weight: 600;
  color: #333;
  white-space: nowrap;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary  { background: #4a90d9; color: #fff; }
.btn-success  { background: #27ae60; color: #fff; }
.btn-info     { background: #17a2b8; color: #fff; }
.btn-secondary { background: #eee; color: #333; }

.resultado {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
  font-size: 0.95rem;
}

.tag {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
}

.tag-ok   { background: #d4edda; color: #155724; }
.tag-info { background: #d1ecf1; color: #0c5460; }

.msg-erro {
  color: #c0392b;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}
</style>
