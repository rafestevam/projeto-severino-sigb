import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { CanceledError } from 'axios'
import api from '@/services/api'
import { DEBOUNCE_MS, TAMANHO_PAGINA, useCatalogoStore } from '@/stores/catalogo'

vi.mock('@/services/api', () => ({ default: { get: vi.fn() } }))

const get = vi.mocked(api.get)

function obra(id: string) {
  return { id, titulo: `Obra ${id}`, autores: ['A'], capa_url: null, categoria: 'C', disponivel: true }
}

function pagina(ids: string[], total: number, page = 1) {
  return { data: { items: ids.map(obra), total, page, page_size: TAMANHO_PAGINA } }
}

describe('useCatalogoStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    get.mockReset()
    vi.useFakeTimers()
  })
  afterEach(() => vi.useRealTimers())

  it('busca com debounce: só a última digitação dispara requisição', async () => {
    get.mockResolvedValue(pagina(['1'], 1))
    const store = useCatalogoStore()

    store.buscar('m')
    store.buscar('ma')
    store.buscar('machado')
    expect(get).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(DEBOUNCE_MS)

    expect(get).toHaveBeenCalledTimes(1)
    expect(get.mock.calls[0][1]?.params).toEqual({ q: 'machado', page: 1, page_size: TAMANHO_PAGINA })
  })

  it('termo vazio não envia q', async () => {
    get.mockResolvedValue(pagina([], 0))
    const store = useCatalogoStore()

    await store.carregarInicial()

    expect(get.mock.calls[0][1]?.params.q).toBeUndefined()
    expect(store.carregou).toBe(true)
  })

  it('cancela a requisição anterior ainda em voo', async () => {
    let primeiroSignal: AbortSignal | undefined
    get.mockImplementationOnce((_url, config) => {
      primeiroSignal = config?.signal as AbortSignal
      return new Promise((_, reject) =>
        primeiroSignal!.addEventListener('abort', () => reject(new CanceledError())),
      )
    })
    get.mockResolvedValueOnce(pagina(['2'], 1))
    const store = useCatalogoStore()

    const primeira = store.carregarInicial()
    await store.carregarInicial()
    await primeira

    expect(primeiroSignal?.aborted).toBe(true)
    expect(store.itens.map((o) => o.id)).toEqual(['2'])
    expect(store.erro).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('carregarMais acrescenta a próxima página até atingir o total', async () => {
    get.mockResolvedValueOnce(pagina(['1', '2'], 3)).mockResolvedValueOnce(pagina(['3'], 3, 2))
    const store = useCatalogoStore()

    await store.carregarInicial()
    await store.carregarMais()
    await store.carregarMais()

    expect(get).toHaveBeenCalledTimes(2)
    expect(get.mock.calls[1][1]?.params.page).toBe(2)
    expect(store.itens.map((o) => o.id)).toEqual(['1', '2', '3'])
    expect(store.temMais).toBe(false)
  })

  it('expõe mensagem de erro', async () => {
    get.mockRejectedValue({ response: { status: 500, data: { detail: 'falhou' } } })
    const store = useCatalogoStore()

    await store.carregarInicial()

    expect(store.erro).toBe('falhou')
  })
})
