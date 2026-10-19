import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import api from '@/services/api'
import { useObraPublicaStore } from '@/stores/obraPublica'

vi.mock('@/services/api', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

const get = vi.mocked(api.get)
const post = vi.mocked(api.post)

const OBRA = {
  id: 'o1', titulo: 'T', autores: ['A'], capa_url: null, categoria: 'C', disponivel: false,
  editora: 'E', ano: 2000, sinopse: null, exemplares_disponiveis: 0, exemplares_emprestados: 1,
  posicao_ranking: 2,
}

describe('useObraPublicaStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    get.mockReset()
    post.mockReset()
  })

  it('carrega o detalhe público', async () => {
    get.mockResolvedValue({ data: OBRA })
    const store = useObraPublicaStore()

    await store.carregar('o1')

    expect(get).toHaveBeenCalledWith('/obras/o1/publico')
    expect(store.obra).toEqual(OBRA)
  })

  it('404 vira "não encontrada" sem mensagem de erro', async () => {
    get.mockRejectedValue({ response: { status: 404 } })
    const store = useObraPublicaStore()

    await store.carregar('x')

    expect(store.naoEncontrada).toBe(true)
    expect(store.erro).toBeNull()
  })

  it('reserva pelo endpoint do próprio leitor, sem leitor_id', async () => {
    get.mockResolvedValue({ data: OBRA })
    post.mockResolvedValue({ data: { posicao_fila: 3 } })
    const store = useObraPublicaStore()
    await store.carregar('o1')

    await store.reservar()

    expect(post).toHaveBeenCalledWith('/reservas/minhas', { obra_id: 'o1' })
    expect(store.posicaoFila).toBe(3)
  })

  it.each([
    [400, 'pendente de ativação'],
    [403, 'cadastro de leitor vinculado'],
    [409, 'já tem uma reserva'],
  ])('erro %i vira mensagem amigável', async (status, trecho) => {
    get.mockResolvedValue({ data: OBRA })
    post.mockRejectedValue({ response: { status } })
    const store = useObraPublicaStore()
    await store.carregar('o1')

    await store.reservar()

    expect(store.erroReserva).toContain(trecho)
    expect(store.posicaoFila).toBeNull()
  })
})
