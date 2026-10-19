import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { papeisDoToken, useAuthStore } from '@/stores/auth'

function tokenCom(roles: string[]): string {
  const payload = btoa(JSON.stringify({ realm_access: { roles } }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
  return `h.${payload}.s`
}

describe('papeisDoToken', () => {
  it('lê realm_access.roles', () => expect(papeisDoToken(tokenCom(['leitor']))).toEqual(['leitor']))
  it('devolve lista vazia para token malformado', () => expect(papeisDoToken('lixo')).toEqual([]))
})

describe('useAuthStore', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('começa anônimo', () => {
    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(false)
    expect(auth.role).toBeNull()
    expect(auth.isStaff).toBe(false)
  })

  it.each([
    [['leitor'], 'leitor', false],
    [['operador', 'leitor'], 'operador', true],
    [['admin', 'operador'], 'admin', true],
    [['outro'], null, false],
  ])('roles %j → role %s (staff=%s)', (roles, role, staff) => {
    const auth = useAuthStore()
    auth.token = tokenCom(roles)
    expect(auth.isAuthenticated).toBe(true)
    expect(auth.role).toBe(role)
    expect(auth.isStaff).toBe(staff)
  })
})
