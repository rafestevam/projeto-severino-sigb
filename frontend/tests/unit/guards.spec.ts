import { describe, expect, it, vi } from 'vitest'
import { resolverAcesso, rotaInicial, type EstadoAuth } from '@/router/guards'
import type { Papel } from '@/stores/auth'

function auth(role: Papel | null): EstadoAuth & { login: ReturnType<typeof vi.fn> } {
  return {
    isAuthenticated: role !== null,
    isStaff: role === 'admin' || role === 'operador',
    role,
    login: vi.fn().mockResolvedValue(undefined),
  }
}

const ORIGIN = 'https://biblioteca.local'
const rotaPublica = { fullPath: '/catalogo', meta: { public: true } }
const rotaBalcao = { fullPath: '/balcao/checkout?x=1', meta: { requiresAuth: true, roles: ['admin', 'operador'] as Papel[] } }
const rotaAdmin = { fullPath: '/inventario', meta: { requiresAuth: true, roles: ['admin'] as Papel[] } }

describe('resolverAcesso', () => {
  it('libera rotas públicas para visitante anônimo', () => {
    const a = auth(null)
    expect(resolverAcesso(rotaPublica, a, ORIGIN)).toBe(true)
    expect(a.login).not.toHaveBeenCalled()
  })

  it('pede login voltando para a mesma URL quando não há sessão', () => {
    const a = auth(null)
    expect(resolverAcesso(rotaBalcao, a, ORIGIN)).toBe(false)
    expect(a.login).toHaveBeenCalledWith(`${ORIGIN}/balcao/checkout?x=1`)
  })

  it('libera o balcão para operador', () => {
    expect(resolverAcesso(rotaBalcao, auth('operador'), ORIGIN)).toBe(true)
  })

  it('manda leitor de volta ao catálogo ao tentar o balcão', () => {
    expect(resolverAcesso(rotaBalcao, auth('leitor'), ORIGIN)).toBe('/catalogo')
  })

  it('manda operador ao checkout ao tentar rota de admin', () => {
    expect(resolverAcesso(rotaAdmin, auth('operador'), ORIGIN)).toBe('/balcao/checkout')
  })

  it('libera rota de admin para admin', () => {
    expect(resolverAcesso(rotaAdmin, auth('admin'), ORIGIN)).toBe(true)
  })
})

describe('rotaInicial', () => {
  it('equipe vai ao balcão', () => expect(rotaInicial({ isStaff: true })).toBe('/balcao/checkout'))
  it('leitor e visitante vão ao catálogo', () => expect(rotaInicial({ isStaff: false })).toBe('/catalogo'))
})
