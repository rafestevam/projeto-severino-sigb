import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import { extrairMensagem, statusHttp } from '@/services/erros'

export interface ObraPublicaDetalhe {
  id: string
  titulo: string
  autores: string[]
  capa_url: string | null
  categoria: string
  disponivel: boolean
  editora: string
  ano: number
  sinopse: string | null
  exemplares_disponiveis: number
  exemplares_emprestados: number
  posicao_ranking: number | null
}

interface ReservaOut {
  posicao_fila: number | null
}

/** Só as 10 obras mais emprestadas recebem o selo "Preferidos da Galera". */
export const LIMITE_PREFERIDOS = 10

const MENSAGENS_RESERVA: Record<number, string> = {
  400: 'Seu cadastro ainda está pendente de ativação no balcão, ou a obra já tem exemplar disponível.',
  401: 'Sua sessão expirou. Entre novamente para reservar.',
  403: 'Não encontramos um cadastro de leitor vinculado ao seu e-mail. Procure o balcão.',
  409: 'Você já tem uma reserva para esta obra.',
}

/**
 * useObraPublicaStore — detalhes públicos de uma obra e reserva pelo OPAC (US-029).
 */
export const useObraPublicaStore = defineStore('obraPublica', () => {
  const obra = ref<ObraPublicaDetalhe | null>(null)
  const loading = ref(false)
  const erro = ref<string | null>(null)
  const naoEncontrada = ref(false)
  const reservando = ref(false)
  const posicaoFila = ref<number | null>(null)
  const erroReserva = ref<string | null>(null)

  async function carregar(id: string): Promise<void> {
    loading.value = true
    erro.value = null
    naoEncontrada.value = false
    obra.value = null
    try {
      const { data } = await api.get<ObraPublicaDetalhe>(`/obras/${id}/publico`)
      obra.value = data
    } catch (err: unknown) {
      const status = statusHttp(err)
      naoEncontrada.value = status === 404 || status === 422
      erro.value = naoEncontrada.value ? null : extrairMensagem(err, 'Não foi possível carregar a obra.')
    } finally {
      loading.value = false
    }
  }

  async function reservar(): Promise<void> {
    if (!obra.value) return
    reservando.value = true
    erroReserva.value = null
    posicaoFila.value = null
    try {
      const { data } = await api.post<ReservaOut>('/reservas/minhas', { obra_id: obra.value.id })
      posicaoFila.value = data.posicao_fila
    } catch (err: unknown) {
      const status = statusHttp(err)
      erroReserva.value =
        (status !== null && MENSAGENS_RESERVA[status]) || 'Não foi possível concluir a reserva.'
    } finally {
      reservando.value = false
    }
  }

  function limparReserva(): void {
    posicaoFila.value = null
    erroReserva.value = null
  }

  return {
    obra, loading, erro, naoEncontrada,
    reservando, posicaoFila, erroReserva,
    carregar, reservar, limparReserva,
  }
})
