import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

interface InventarioDivergencias {
  encontrados: string[]
  nao_bipados: Array<{ id: string; codigo_qr: string; titulo_obra?: string }>
  nao_esperados: string[]
}

/**
 * useInventarioStore — estado e ações para a tela de inventário com scan contínuo.
 *
 * Fluxo:
 *   1. iniciarScan() → habilita bipagem contínua.
 *   2. adicionarCodigo(codigoQr) → acumula na lista codigosBipados.
 *   3. processar(localizacao) → POST /api/inventario/scan; popula divergencias.
 *   4. darBaixa(exemplarId, motivo) → POST /api/exemplares/{id}/baixar.
 */
export const useInventarioStore = defineStore('inventario', () => {
  const scanAtivo = ref(false)
  const codigosBipados = ref<string[]>([])
  const divergencias = ref<InventarioDivergencias | null>(null)
  const loading = ref(false)
  const erro = ref<string | null>(null)

  function iniciarScan(): void {
    scanAtivo.value = true
    codigosBipados.value = []
    divergencias.value = null
    erro.value = null
  }

  function adicionarCodigo(codigoQr: string): void {
    if (!codigosBipados.value.includes(codigoQr)) {
      codigosBipados.value.push(codigoQr)
    }
  }

  async function processar(localizacao: string): Promise<void> {
    erro.value = null
    loading.value = true
    try {
      const response = await api.post<InventarioDivergencias>('/inventario/scan', {
        codigos_qr: codigosBipados.value,
        localizacao,
      })
      divergencias.value = response.data
      scanAtivo.value = false
    } catch (err: unknown) {
      erro.value = _extrairMensagem(err, 'Erro ao processar inventário.')
    } finally {
      loading.value = false
    }
  }

  async function darBaixa(exemplarId: string, motivo: string): Promise<void> {
    erro.value = null
    loading.value = true
    try {
      await api.post(`/exemplares/${exemplarId}/baixar`, { motivo })
      // Remove da lista nao_bipados após baixa bem-sucedida
      if (divergencias.value) {
        divergencias.value.nao_bipados = divergencias.value.nao_bipados.filter(
          (e) => e.id !== exemplarId,
        )
      }
    } catch (err: unknown) {
      erro.value = _extrairMensagem(err, 'Erro ao dar baixa no exemplar.')
    } finally {
      loading.value = false
    }
  }

  function resetar(): void {
    scanAtivo.value = false
    codigosBipados.value = []
    divergencias.value = null
    loading.value = false
    erro.value = null
  }

  return {
    scanAtivo, codigosBipados, divergencias, loading, erro,
    iniciarScan, adicionarCodigo, processar, darBaixa, resetar,
  }
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
