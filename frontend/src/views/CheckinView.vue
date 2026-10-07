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
        class="qr-input"
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

<style scoped>
.checkin-view {
  max-width: 700px;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
  color: #1c1c1e;
}

.subtitle {
  color: #666;
  margin-bottom: 1.5rem;
}

.scan-area {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.qr-input {
  flex: 1;
  padding: 1rem;
  font-size: 1.25rem;
  border: 2px solid #4a90d9;
  border-radius: 8px;
  outline: none;
}

.qr-input:focus {
  border-color: #1e6ec8;
  box-shadow: 0 0 0 3px rgba(74, 144, 217, 0.2);
}

.loading-badge {
  font-size: 0.9rem;
  color: #888;
  font-style: italic;
}

.feedback {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  padding: 1.25rem 1.5rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.feedback-sucesso {
  background: #d4edda;
  border: 2px solid #27ae60;
}

.feedback-erro {
  background: #f8d7da;
  border: 2px solid #c0392b;
}

.feedback-icon {
  font-size: 2.5rem;
  font-weight: 900;
  line-height: 1;
}

.feedback-sucesso .feedback-icon { color: #155724; }
.feedback-erro .feedback-icon { color: #721c24; }

.feedback-titulo {
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 0.35rem;
}

.feedback-sucesso .feedback-titulo { color: #155724; }
.feedback-erro .feedback-titulo { color: #721c24; }

.feedback-detalhe {
  font-size: 1rem;
  color: #333;
  margin: 0.1rem 0;
}
</style>
