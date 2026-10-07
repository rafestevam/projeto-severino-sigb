import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

interface ExemplaresPorEstado {
  disponivel: number
  emprestado: number
  baixado: number
}

interface TopObra {
  obra_id: string
  titulo: string
  total_emprestimos: number
}

interface DashboardMetricas {
  total_obras: number
  total_exemplares: number
  total_leitores_ativos: number
  exemplares_por_estado: ExemplaresPorEstado
  top_obras_emprestadas: TopObra[]
  taxa_perdas: number
  total_doacoes: number
}

/**
 * useDashboardStore — estado e ações para a tela de dashboard de métricas.
 */
export const useDashboardStore = defineStore('dashboard', () => {
  const metricas = ref<DashboardMetricas | null>(null)
  const loading = ref(false)
  const erro = ref<string | null>(null)

  async function carregar(): Promise<void> {
    erro.value = null
    loading.value = true
    try {
      const response = await api.get<DashboardMetricas>('/relatorios/dashboard')
      metricas.value = response.data
    } catch (err: unknown) {
      erro.value = _extrairMensagem(err, 'Erro ao carregar métricas do dashboard.')
    } finally {
      loading.value = false
    }
  }

  return { metricas, loading, erro, carregar }
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
