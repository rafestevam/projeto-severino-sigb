import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

interface Metadados {
  titulo: string | null
  autores: string[] | null
  editora: string | null
  ano: number | null
  capa_url: string | null
  categoria: string | null
}

interface ObraOut {
  id: string
  isbn: string | null
  titulo: string
  autores: string[]
  editora: string
  ano: number
  categoria: string
  capa_url: string | null
}

interface ExemplarOut {
  id: string
  codigo_qr: string
}

/**
 * useCatalogacaoStore — estado e ações para a tela de catalogação por ISBN.
 *
 * Fluxo:
 *   1. buscarIsbn(isbn) → POST /api/obras/isbn/{isbn}; preenche metadados.
 *   2. salvar() → POST /api/obras + POST /api/obras/{id}/exemplares.
 *   3. imprimirEtiquetas() → abre PDF em nova aba.
 */
export const useCatalogacaoStore = defineStore('catalogacao', () => {
  const metadados = ref<Metadados>({
    titulo: null,
    autores: null,
    editora: null,
    ano: null,
    capa_url: null,
    categoria: null,
  })
  const quantidadeExemplares = ref(1)
  const obraCriada = ref<ObraOut | null>(null)
  const exemplaresCriados = ref<ExemplarOut[]>([])
  const erro = ref<string | null>(null)
  const loading = ref(false)
  const etiquetaUrl = ref<string | null>(null)

  async function buscarIsbn(isbn: string): Promise<void> {
    erro.value = null
    loading.value = true
    try {
      const response = await api.post<Metadados>(`/obras/isbn/${isbn}`)
      metadados.value = response.data
    } catch (err: unknown) {
      erro.value = _extrairMensagem(err, 'Não foi possível buscar metadados para este ISBN.')
    } finally {
      loading.value = false
    }
  }

  async function salvar(): Promise<void> {
    erro.value = null
    loading.value = true
    try {
      // Cria a obra
      const obraResponse = await api.post<ObraOut>('/obras', {
        isbn: null,
        titulo: metadados.value.titulo ?? '',
        autores: metadados.value.autores ?? [],
        editora: metadados.value.editora ?? '',
        ano: metadados.value.ano ?? 0,
        capa_url: metadados.value.capa_url,
        categoria: metadados.value.categoria ?? '',
      })
      obraCriada.value = obraResponse.data

      // Cria os exemplares
      const exemplaresResponse = await api.post<ExemplarOut[]>(
        `/obras/${obraCriada.value.id}/exemplares`,
        { quantidade: quantidadeExemplares.value, localizacao_estante: 'A-01' },
      )
      exemplaresCriados.value = exemplaresResponse.data

      if (exemplaresCriados.value.length > 0) {
        etiquetaUrl.value = `/api/exemplares/${exemplaresCriados.value[0].codigo_qr}/etiqueta.pdf`
      }
    } catch (err: unknown) {
      erro.value = _extrairMensagem(err, 'Erro ao salvar obra e exemplares.')
    } finally {
      loading.value = false
    }
  }

  function imprimirEtiquetas(): void {
    if (etiquetaUrl.value) {
      window.open(etiquetaUrl.value, '_blank')
    }
  }

  function resetar(): void {
    metadados.value = {
      titulo: null, autores: null, editora: null,
      ano: null, capa_url: null, categoria: null,
    }
    quantidadeExemplares.value = 1
    obraCriada.value = null
    exemplaresCriados.value = []
    erro.value = null
    etiquetaUrl.value = null
  }

  return {
    metadados, quantidadeExemplares, obraCriada, exemplaresCriados,
    erro, loading, etiquetaUrl,
    buscarIsbn, salvar, imprimirEtiquetas, resetar,
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
