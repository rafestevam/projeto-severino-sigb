<template>
  <div class="modal-overlay" @click.self="$emit('cancelar')">
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-titulo">
      <h3 id="modal-titulo" class="modal-titulo">Dar Baixa no Exemplar</h3>
      <p class="modal-desc">
        Exemplar: <strong>{{ codigoQr }}</strong>
      </p>
      <div class="form-field">
        <label for="motivo-input">Motivo da baixa *</label>
        <input
          id="motivo-input"
          v-model="motivo"
          type="text"
          class="input"
          placeholder="Ex: extraviado, danificado…"
          @keydown.enter="handleConfirmar"
          autofocus
        />
      </div>
      <div class="modal-acoes">
        <button
          class="btn btn-danger"
          :disabled="!motivo.trim()"
          @click="handleConfirmar"
        >
          Confirmar Baixa
        </button>
        <button class="btn btn-secondary" @click="$emit('cancelar')">
          Cancelar
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

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

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: #fff;
  border-radius: 8px;
  padding: 1.5rem;
  width: 420px;
  max-width: 90vw;
}

.modal-titulo {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.modal-desc {
  font-size: 0.9rem;
  color: #555;
  margin-bottom: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 1rem;
}

.form-field label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #333;
}

.input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.95rem;
}

.modal-acoes {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
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
.btn-danger    { background: #c0392b; color: #fff; }
.btn-secondary { background: #eee; color: #333; }
</style>
