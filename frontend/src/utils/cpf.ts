/**
 * Validação de CPF no cliente (US-030).
 *
 * Mesmo algoritmo do value object `Cpf` do backend (app/domain/value_objects/cpf.py):
 * 11 dígitos, sem sequência repetida e com os dois dígitos verificadores corretos.
 */

const TAMANHO_CPF = 11

export function somenteDigitos(texto: string): string {
  return texto.replace(/\D/g, '')
}

function digitoVerificador(digitos: string): number {
  const pesoInicial = digitos.length + 1
  const soma = [...digitos].reduce((acc, d, i) => acc + Number(d) * (pesoInicial - i), 0)
  const resto = soma % 11
  return resto < 2 ? 0 : 11 - resto
}

export function validarCpf(texto: string): boolean {
  const digitos = somenteDigitos(texto)
  if (digitos.length !== TAMANHO_CPF || new Set(digitos).size === 1) return false
  const primeiro = digitoVerificador(digitos.slice(0, 9))
  const segundo = digitoVerificador(digitos.slice(0, 10))
  return digitos.slice(9) === `${primeiro}${segundo}`
}

/** Aplica a máscara 000.000.000-00 progressivamente, enquanto o usuário digita. */
export function formatarCpf(texto: string): string {
  const d = somenteDigitos(texto).slice(0, TAMANHO_CPF)
  if (d.length <= 3) return d
  if (d.length <= 6) return `${d.slice(0, 3)}.${d.slice(3)}`
  if (d.length <= 9) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`
}
