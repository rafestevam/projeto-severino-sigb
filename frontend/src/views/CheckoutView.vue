<template>
  <div class="checkout-view">
    <h1 class="page-title">Check-Out — Empréstimo</h1>

    <!-- Seção: busca de leitor por CPF -->
    <section class="card">
      <h2>1. Identificar Leitor</h2>
      <div class="form-row">
        <input
          v-model="cpf"
          type="text"
          placeholder="CPF do leitor (somente números)"
          class="input"
          @keydown.enter="handleBuscarLeitor"
          :disabled="store.loading"
        />
        <button class="btn btn-primary" @click="handleBuscarLeitor" :disabled="store.loading">
          Buscar
        </button>
      </div>
      <p v-if="store.erroLeitor" class="msg-erro">{{ store.erroLeitor }}</p>
      <div v-if="store.leitor" class="resultado">
        <span class="tag tag-ok">✓ Leitor identificado</span>
        <strong>{{ store.leitor.nome }}</strong>
        <span v-if="!store.leitor.ativo" class="tag tag-aviso">Inativo</span>
      </div>
    </section>

    <!-- Seção: leitura do exemplar -->
    <section class="card">
      <h2>2. Bipar Exemplar</h2>
      <div class="form-row">
        <input
          ref="qrInputRef"
          type="text"
          placeholder="Código QR (aponte o leitor aqui)"
          class="input"
          :disabled="store.loading || !store.leitor"
        />
      </div>
      <p v-if="store.erroExemplar" class="msg-erro">{{ store.erroExemplar }}</p>
      <div v-if="store.exemplar" class="resultado">
        <span class="tag tag-ok">✓ Exemplar identificado</span>
        <strong>{{ store.exemplar.titulo_obra ?? store.exemplar.codigo_qr }}</strong>
        <span class="tag tag-info">{{ store.exemplar.estado }}</span>
      </div>
    </section>

    <!-- Seção: confirmação -->
    <section class="card card-acao">
      <p v-if="store.erroCheckout" class="msg-erro">{{ store.erroCheckout }}</p>
      <div class="form-row">
        <button
          class="btn btn-success btn-large"
          :disabled="!store.leitor || !store.exemplar || store.loading"
          @click="store.confirmarCheckout()"
        >
          {{ store.loading ? 'Processando…' : 'Confirmar Empréstimo' }}
        </button>
        <button class="btn btn-secondary" @click="store.resetar()">
          Limpar
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useCheckoutStore } from '@/stores/checkout'
import { useQrScanner } from '@/composables/useQrScanner'

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

<style scoped>
.checkout-view {
  max-width: 700px;
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

.input {
  flex: 1;
  min-width: 200px;
  padding: 0.5rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1rem;
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

.btn-primary {
  background: #4a90d9;
  color: #fff;
}

.btn-success {
  background: #27ae60;
  color: #fff;
}

.btn-secondary {
  background: #eee;
  color: #333;
}

.btn-large {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
}

.resultado {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  font-size: 0.95rem;
}

.tag {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
}

.tag-ok { background: #d4edda; color: #155724; }
.tag-aviso { background: #fff3cd; color: #856404; }
.tag-info { background: #d1ecf1; color: #0c5460; }

.msg-erro {
  color: #c0392b;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}
</style>
