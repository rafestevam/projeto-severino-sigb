import type { RouteLocationNormalized } from 'vue-router'
import type { Papel } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    /** Rota do OPAC, acessível sem login. */
    public?: boolean
    layout?: 'publico' | 'balcao'
    requiresAuth?: boolean
    roles?: Papel[]
  }
}

export const PAPEIS_BALCAO: Papel[] = ['admin', 'operador']

export interface EstadoAuth {
  isAuthenticated: boolean
  isStaff: boolean
  role: Papel | null
  login(redirectUri?: string): Promise<void>
}

/** Destino de `/`: o balcão para a equipe, o catálogo para leitores e visitantes. */
export function rotaInicial(auth: Pick<EstadoAuth, 'isStaff'>): string {
  return auth.isStaff ? '/balcao/checkout' : '/catalogo'
}

/**
 * Guard global: rotas com `requiresAuth` disparam o login do Keycloak voltando
 * para a mesma URL; papéis insuficientes voltam para a rota inicial do usuário.
 */
export function resolverAcesso(
  to: Pick<RouteLocationNormalized, 'meta' | 'fullPath'>,
  auth: EstadoAuth,
  origin: string = window.location.origin,
): true | false | string {
  if (!to.meta.requiresAuth) return true

  if (!auth.isAuthenticated) {
    void auth.login(origin + to.fullPath)
    return false
  }

  const roles = to.meta.roles
  if (roles && (!auth.role || !roles.includes(auth.role))) return rotaInicial(auth)
  return true
}
