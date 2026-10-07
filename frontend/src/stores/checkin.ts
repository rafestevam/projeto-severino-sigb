import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

interface DevolucaoResult {
  exemplar_id: string
  leitor_id: string
  titulo?: string
}

/**
 * useCheckinStore — estado e ações para a tela de check-in (devolução).
 *
 * Fluxo de "1 bip":
 *   1. devolverPorQr(codigoQr) → POST /api/emprestimos/devolver-por-qr
 *      - Em sucesso: popula ultimaDevolucao
 *      - Em erro: popula erro
 */
export const useCheckinStore = defineStore('checkin', () => {
  const ultimaDevolucao = ref<DevolucaoResult | null>(null)
  const erro = ref<string | null>(null)
  const loading = ref(false)

  async function devolverPorQr(codigoQr: string): Promise<void> {
    erro.value = null
    ultimaDevolucao.value = null
    loading.value = true
    try {
      const response = await api.post<DevolucaoResult>('/emprestimos/devolver-por-qr', {
        codigo_qr: codigoQr,
      })
      ultimaDevolucao.value = response.data
    } catch (err: unknown) {
      erro.value = _extrairMensagem(err, 'Nenhum empréstimo ativo encontrado para este QR.')
    } finally {
      loading.value = false
    }
  }

  function resetar(): void {
    ultimaDevolucao.value = null
    erro.value = null
  }

  return { ultimaDevolucao, erro, loading, devolverPorQr, resetar }
})

function _extrairMensagem(err: unknown, fallback: string): string {
  if (
    err &&
    typeof err === 'object' &&
    'response' in err &&
    err.response &&
    typeof err.response === 'object' &&
    'data' in err.response &&
    err.response.data &&
    typeof err.response.data === 'object' &&
    'detail' in err.response.data
  ) {
    return String((err.response.data as Record<string, unknown>).detail)
  }
  return fallback
}
