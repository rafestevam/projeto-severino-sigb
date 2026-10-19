import { describe, expect, it } from 'vitest'
import { formatarCpf, somenteDigitos, validarCpf } from '@/utils/cpf'

describe('validarCpf', () => {
  it.each(['529.982.247-25', '52998224725', '111.444.777-35', '00000000191'])(
    'aceita CPF válido %s',
    (cpf) => expect(validarCpf(cpf)).toBe(true),
  )

  it.each(['529.982.247-24', '12345678900', '52998224715'])(
    'rejeita dígitos verificadores errados %s',
    (cpf) => expect(validarCpf(cpf)).toBe(false),
  )

  it.each(['000.000.000-00', '11111111111'])('rejeita sequência repetida %s', (cpf) =>
    expect(validarCpf(cpf)).toBe(false),
  )

  it.each(['', '123', '5299822472', '529982247250'])('rejeita tamanho inválido "%s"', (cpf) =>
    expect(validarCpf(cpf)).toBe(false),
  )
})

describe('formatarCpf', () => {
  it.each([
    ['5', '5'],
    ['5299', '529.9'],
    ['5299822', '529.982.2'],
    ['52998224725', '529.982.247-25'],
    ['529982247251234', '529.982.247-25'],
    ['529.98a2', '529.982'],
  ])('formata %s como %s', (entrada, esperado) => expect(formatarCpf(entrada)).toBe(esperado))
})

describe('somenteDigitos', () => {
  it('remove máscara', () => expect(somenteDigitos('529.982.247-25')).toBe('52998224725'))
})
