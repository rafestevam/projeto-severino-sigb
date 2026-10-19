import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import api from '@/services/api'
import { MENSAGEM_CPF_INVALIDO, MENSAGEM_JA_CADASTRADO, useCadastroStore } from '@/stores/cadastro'

vi.mock('@/services/api', () => ({ default: { post: vi.fn() } }))

const post = vi.mocked(api.post)

describe('useCadastroStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    post.mockReset()
  })

  it('não envia com CPF inválido', async () => {
    const store = useCadastroStore()
    store.form = { nome: 'Ana', cpf: '111.111.111-11', telefone: '', email: '' }

    await store.enviar()

    expect(store.erroCpf).toBe(MENSAGEM_CPF_INVALIDO)
    expect(post).not.toHaveBeenCalled()
  })

  it('envia CPF normalizado e contatos vazios como null', async () => {
    post.mockResolvedValue({ data: { status: 'pendente' } })
    const store = useCadastroStore()
    store.form = { nome: ' Ana Lima ', cpf: '529.982.247-25', telefone: ' ', email: '' }

    await store.enviar()

    expect(post).toHaveBeenCalledWith('/leitores', {
      nome: 'Ana Lima', cpf: '52998224725', telefone: null, email: null,
    })
    expect(store.sucesso).toBe(true)
    expect(store.form.cpf).toBe('')
  })

  it('409 informa cadastro existente sem outros dados', async () => {
    post.mockRejectedValue({ response: { status: 409, data: { detail: 'qualquer' } } })
    const store = useCadastroStore()
    store.form = { nome: 'Ana', cpf: '52998224725', telefone: '', email: '' }

    await store.enviar()

    expect(store.erro).toBe(MENSAGEM_JA_CADASTRADO)
    expect(store.sucesso).toBe(false)
  })

  it('validarCampoCpf limpa o erro quando o CPF fica válido', () => {
    const store = useCadastroStore()
    store.form.cpf = '123'
    expect(store.validarCampoCpf()).toBe(false)
    store.form.cpf = '529.982.247-25'
    expect(store.validarCampoCpf()).toBe(true)
    expect(store.erroCpf).toBeNull()
  })
})
