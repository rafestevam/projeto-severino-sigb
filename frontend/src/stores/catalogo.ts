import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import axios from 'axios'
import api from '@/services/api'
import { extrairMensagem } from '@/services/erros'

export interface ObraPublica {
  id: string
  titulo: string
  autores: string[]
  capa_url: string | null
  categoria: string
  disponivel: boolean
}

interface ObraPublicaList {
  items: ObraPublica[]
  total: number
  page: number
  page_size: number
}

export const TAMANHO_PAGINA = 24
export const DEBOUNCE_MS = 300

/**
 * useCatalogoStore — catálogo público do OPAC (US-028).
 *
 * Fluxo:
 *   1. buscar(termo) → aguarda 300 ms sem digitação e carrega a página 1,
 *      cancelando a requisição anterior ainda em voo.
 *   2. carregarMais() → acrescenta a próxima página (scroll infinito).
 */
export const useCatalogoStore = defineStore('catalogo', () => {
  const termo = ref('')
  const itens = ref<ObraPublica[]>([])
  const page = ref(0)
  const total = ref(0)
  const loading = ref(false)
  const erro = ref<string | null>(null)

  let debounce: ReturnType<typeof setTimeout> | null = null
  let requisicaoEmVoo: AbortController | null = null

  const temMais = computed(() => itens.value.length < total.value)
  const carregou = computed(() => page.value > 0)

  async function carregarPagina(numero: number): Promise<void> {
    requisicaoEmVoo?.abort()
    const controller = new AbortController()
    requisicaoEmVoo = controller
    loading.value = true
    erro.value = null
    try {
      const { data } = await api.get<ObraPublicaList>('/obras/publico', {
        params: { q: termo.value.trim() || undefined, page: numero, page_size: TAMANHO_PAGINA },
        signal: controller.signal,
      })
      itens.value = numero === 1 ? data.items : [...itens.value, ...data.items]
      total.value = data.total
      page.value = numero
    } catch (err: unknown) {
      if (axios.isCancel(err)) return
      erro.value = extrairMensagem(err, 'Não foi possível carregar o catálogo.')
    } finally {
      if (requisicaoEmVoo === controller) {
        requisicaoEmVoo = null
        loading.value = false
      }
    }
  }

  function buscar(novoTermo: string): void {
    termo.value = novoTermo
    if (debounce) clearTimeout(debounce)
    debounce = setTimeout(() => {
      debounce = null
      void carregarPagina(1)
    }, DEBOUNCE_MS)
  }

  function carregarInicial(): Promise<void> {
    return carregarPagina(1)
  }

  async function carregarMais(): Promise<void> {
    if (loading.value || !temMais.value) return
    await carregarPagina(page.value + 1)
  }

  return {
    termo, itens, page, total, loading, erro, temMais, carregou,
    buscar, carregarInicial, carregarMais,
  }
})
