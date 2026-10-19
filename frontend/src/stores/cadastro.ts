import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import { extrairMensagem, statusHttp } from '@/services/erros'
import { somenteDigitos, validarCpf } from '@/utils/cpf'

export interface FormCadastro {
  nome: string
  cpf: string
  telefone: string
  email: string
}

export const MENSAGEM_CPF_INVALIDO = 'CPF inválido. Confira os números digitados.'
export const MENSAGEM_JA_CADASTRADO =
  'Já existe um cadastro para este CPF. Procure o balcão da biblioteca.'

export const MENSAGEM_DADOS_INVALIDOS = 'Confira os dados informados: nome, CPF e e-mail.'

function formVazio(): FormCadastro {
  return { nome: '', cpf: '', telefone: '', email: '' }
}

/**
 * useCadastroStore — pré-cadastro público de leitor (US-030).
 *
 * O CPF é validado aqui (formato e dígitos verificadores) antes do envio; a API
 * valida de novo e armazena apenas o hash.
 */
export const useCadastroStore = defineStore('cadastro', () => {
  const form = ref<FormCadastro>(formVazio())
  const erroCpf = ref<string | null>(null)
  const erro = ref<string | null>(null)
  const loading = ref(false)
  const sucesso = ref(false)

  function validarCampoCpf(): boolean {
    erroCpf.value = validarCpf(form.value.cpf) ? null : MENSAGEM_CPF_INVALIDO
    return erroCpf.value === null
  }

  async function enviar(): Promise<void> {
    erro.value = null
    if (!validarCampoCpf()) return
    loading.value = true
    try {
      await api.post('/leitores', {
        nome: form.value.nome.trim(),
        cpf: somenteDigitos(form.value.cpf),
        telefone: form.value.telefone.trim() || null,
        email: form.value.email.trim() || null,
      })
      sucesso.value = true
      form.value = formVazio()
    } catch (err: unknown) {
      const status = statusHttp(err)
      if (status === 409) erro.value = MENSAGEM_JA_CADASTRADO
      else if (status === 422) erro.value = extrairMensagem(err, MENSAGEM_DADOS_INVALIDOS)
      else erro.value = extrairMensagem(err, 'Não foi possível concluir o cadastro.')
    } finally {
      loading.value = false
    }
  }

  function resetar(): void {
    form.value = formVazio()
    erroCpf.value = null
    erro.value = null
    sucesso.value = false
  }

  return { form, erroCpf, erro, loading, sucesso, validarCampoCpf, enviar, resetar }
})
