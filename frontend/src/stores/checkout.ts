import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

interface LeitorOut {
  id: string
  nome: string
  ativo: boolean
}

interface ExemplarOut {
  id: string
  codigo_qr: string
  obra_id: string
  titulo_obra: string | null
  estado: string
}

/**
 * useCheckoutStore — estado e ações para a tela de check-out.
 *
 * Fluxo:
 *   1. buscarLeitor(cpf) → popula `leitor` ou `erroLeitor`
 *   2. buscarExemplar(codigoQr) → popula `exemplar` ou `erroExemplar`
 *   3. confirmarCheckout() → POST /api/emprestimos; reseta estado
 */
export const useCheckoutStore = defineStore('checkout', () => {
  const leitor = ref<LeitorOut | null>(null)
  const exemplar = ref<ExemplarOut | null>(null)
  const erroLeitor = ref<string | null>(null)
  const erroExemplar = ref<string | null>(null)
  const erroCheckout = ref<string | null>(null)
  const loading = ref(false)
  const sucesso = ref(false)

  async function buscarLeitor(cpf: string): Promise<void> {
    erroLeitor.value = null
    leitor.value = null
    loading.value = true
    try {
      const response = await api.get<LeitorOut>('/leitores', { params: { cpf } })
      leitor.value = response.data
    } catch (err: unknown) {
      erroLeitor.value = _extrairMensagem(err, 'Leitor não encontrado para o CPF informado.')
    } finally {
      loading.value = false
    }
  }

  async function buscarExemplar(codigoQr: string): Promise<void> {
    erroExemplar.value = null
    exemplar.value = null
    loading.value = true
    try {
      const response = await api.get<ExemplarOut>(`/exemplares/by-qr/${codigoQr}`)
      exemplar.value = response.data
    } catch (err: unknown) {
      erroExemplar.value = _extrairMensagem(err, 'Exemplar não encontrado para o código QR.')
    } finally {
      loading.value = false
    }
  }

  async function confirmarCheckout(): Promise<void> {
    if (!leitor.value || !exemplar.value) return
    erroCheckout.value = null
    loading.value = true
    try {
      await api.post('/emprestimos', {
        exemplar_id: exemplar.value.id,
        leitor_id: leitor.value.id,
      })
      sucesso.value = true
      resetar()
    } catch (err: unknown) {
      erroCheckout.value = _extrairMensagem(err, 'Erro ao confirmar empréstimo.')
    } finally {
      loading.value = false
    }
  }

  function resetar(): void {
    leitor.value = null
    exemplar.value = null
    erroLeitor.value = null
    erroExemplar.value = null
    erroCheckout.value = null
    sucesso.value = false
  }

  return {
    leitor, exemplar,
    erroLeitor, erroExemplar, erroCheckout,
    loading, sucesso,
    buscarLeitor, buscarExemplar, confirmarCheckout, resetar,
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
