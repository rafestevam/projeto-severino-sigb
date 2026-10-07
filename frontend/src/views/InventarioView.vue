<template>
  <div class="inventario-view">
    <h1 class="page-title">Inventário</h1>

    <!-- Controles iniciais -->
    <section class="card" v-if="!store.scanAtivo && !store.divergencias">
      <div class="form-row">
        <label class="label-inline">Localização:</label>
        <input v-model="localizacao" type="text" class="input" placeholder="Ex: Estante A-01" />
        <button class="btn btn-primary" @click="handleIniciarScan" :disabled="!localizacao.trim()">
          Iniciar Scan
        </button>
      </div>
      <p v-if="store.erro" class="msg-erro">{{ store.erro }}</p>
    </section>

    <!-- Campo de bipagem contínua -->
    <section class="card" v-if="store.scanAtivo">
      <h2>Bipagem contínua — {{ store.codigosBipados.length }} código(s) lidos</h2>
      <div class="form-row">
        <input
          ref="qrInputRef"
          type="text"
          placeholder="Aponte o leitor de QR aqui…"
          class="qr-input"
        />
      </div>
      <ul class="codigo-list" v-if="store.codigosBipados.length > 0">
        <li v-for="codigo in store.codigosBipados" :key="codigo" class="codigo-item">
          {{ codigo }}
        </li>
      </ul>
      <div class="form-row btn-row">
        <button
          class="btn btn-success"
          :disabled="store.loading || store.codigosBipados.length === 0"
          @click="store.processar(localizacao)"
        >
          {{ store.loading ? 'Processando…' : 'Processar Inventário' }}
        </button>
        <button class="btn btn-secondary" @click="store.resetar()">
          Cancelar
        </button>
      </div>
    </section>

    <!-- Resultados de divergências -->
    <template v-if="store.divergencias">
      <div class="form-row btn-row" style="margin-bottom: 1rem;">
        <button class="btn btn-secondary" @click="store.resetar()">Novo Inventário</button>
      </div>

      <!-- Encontrados -->
      <section class="card">
        <h2 class="section-ok">
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
        <h2 class="section-aviso">
          ⚠ Não bipados ({{ store.divergencias.nao_bipados.length }})
        </h2>
        <p v-if="store.divergencias.nao_bipados.length === 0" class="vazio">Nenhum.</p>
        <table class="tabela" v-else>
          <thead>
            <tr>
              <th>Código QR</th>
              <th>Título</th>
              <th>Ação</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="exemplar in store.divergencias.nao_bipados" :key="exemplar.id">
              <td>{{ exemplar.codigo_qr }}</td>
              <td>{{ exemplar.titulo_obra ?? '—' }}</td>
              <td>
                <button
                  class="btn btn-danger btn-sm"
                  @click="abrirModalBaixa(exemplar.id, exemplar.codigo_qr)"
                >
                  Dar Baixa
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Não esperados -->
      <section class="card">
        <h2 class="section-erro">
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
import { useInventarioStore } from '@/stores/inventario'
import { useQrScanner } from '@/composables/useQrScanner'
import ModalBaixa from '@/components/ModalBaixa.vue'

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

<style scoped>
.inventario-view {
  max-width: 900px;
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
}

.section-ok    { color: #155724; }
.section-aviso { color: #856404; }
.section-erro  { color: #721c24; }

.form-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.btn-row {
  margin-top: 0.75rem;
}

.input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.95rem;
}

.qr-input {
  flex: 1;
  padding: 0.75rem;
  font-size: 1.1rem;
  border: 2px solid #4a90d9;
  border-radius: 6px;
}

.label-inline {
  font-size: 0.9rem;
  font-weight: 600;
  white-space: nowrap;
}

.codigo-list {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.codigo-item {
  background: #e9ecef;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-family: monospace;
}

.codigo-erro {
  background: #f8d7da;
  color: #721c24;
}

.tabela {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.tabela th, .tabela td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e0e0e0;
  text-align: left;
}

.tabela th {
  background: #f5f5f5;
  font-weight: 600;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
}

.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-sm       { padding: 0.3rem 0.6rem; font-size: 0.8rem; }
.btn-primary   { background: #4a90d9; color: #fff; }
.btn-success   { background: #27ae60; color: #fff; }
.btn-danger    { background: #c0392b; color: #fff; }
.btn-secondary { background: #eee; color: #333; }

.vazio { font-size: 0.9rem; color: #888; }

.msg-erro {
  color: #c0392b;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}
</style>
