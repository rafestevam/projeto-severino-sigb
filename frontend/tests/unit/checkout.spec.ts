import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import api from '@/services/api'
import { useCheckoutStore } from '@/stores/checkout'

vi.mock('@/services/api', () => ({ default: { get: vi.fn(), patch: vi.fn(), post: vi.fn() } }))

const get = vi.mocked(api.get)
const patch = vi.mocked(api.patch)

describe('useCheckoutStore — ativação de leitor pendente (US-030)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    get.mockReset()
    patch.mockReset()
  })

  it('busca leitor com CPF normalizado', async () => {
    get.mockResolvedValue({ data: { id: 'l1', nome: 'Ana', ativo: false, status: 'pendente' } })
    const store = useCheckoutStore()

    await store.buscarLeitor('529.982.247-25')

    expect(get).toHaveBeenCalledWith('/leitores', { params: { cpf: '52998224725' } })
    expect(store.leitor?.status).toBe('pendente')
  })

  it('ativarLeitor atualiza o leitor para ativo', async () => {
    get.mockResolvedValue({ data: { id: 'l1', nome: 'Ana', ativo: false, status: 'pendente' } })
    patch.mockResolvedValue({ data: { id: 'l1', nome: 'Ana', ativo: true, status: 'ativo' } })
    const store = useCheckoutStore()
    await store.buscarLeitor('52998224725')

    await store.ativarLeitor()

    expect(patch).toHaveBeenCalledWith('/leitores/l1/ativar')
    expect(store.leitor?.status).toBe('ativo')
  })

  it('erro na ativação mantém o leitor e mostra a mensagem', async () => {
    get.mockResolvedValue({ data: { id: 'l1', nome: 'Ana', ativo: false, status: 'pendente' } })
    patch.mockRejectedValue({ response: { status: 404, data: { detail: 'Leitor não encontrado: l1' } } })
    const store = useCheckoutStore()
    await store.buscarLeitor('52998224725')

    await store.ativarLeitor()

    expect(store.erroLeitor).toBe('Leitor não encontrado: l1')
    expect(store.leitor?.status).toBe('pendente')
  })
})
