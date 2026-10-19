import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type Keycloak from 'keycloak-js'

export type Papel = 'admin' | 'operador' | 'leitor'

const IS_DEV_AUTH = import.meta.env.VITE_DEV_AUTH === 'true'
// Em modo dev, começa como visitante anônimo para desenvolver o OPAC.
// "Entrar" grava a sessão fictícia no sessionStorage, que sobrevive ao redirect.
const IS_DEV_AUTH_ANON = import.meta.env.VITE_DEV_AUTH_ANON === 'true'
const CHAVE_SESSAO_DEV = 'libsys-dev-auth'

function base64url(texto: string): string {
  return btoa(texto).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

// Token JWT fictício (não assinado) com role 'admin' e e-mail para a reserva online.
const DEV_TOKEN =
  'eyJhbGciOiJub25lIn0.' +
  base64url(
    JSON.stringify({
      sub: 'dev-user',
      name: 'Dev Admin',
      email: 'dev@example.com',
      email_verified: true,
      realm_access: { roles: ['admin'] },
    }),
  ) +
  '.'

export function papeisDoToken(token: string): string[] {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(atob(base64))
    const roles = payload?.realm_access?.roles
    return Array.isArray(roles) ? roles : []
  } catch {
    return []
  }
}

function lerSessaoDev(): boolean {
  try {
    return sessionStorage.getItem(CHAVE_SESSAO_DEV) === '1'
  } catch {
    return false
  }
}

function gravarSessaoDev(ativa: boolean): void {
  try {
    if (ativa) sessionStorage.setItem(CHAVE_SESSAO_DEV, '1')
    else sessionStorage.removeItem(CHAVE_SESSAO_DEV)
  } catch {
    // sessionStorage indisponível (modo privado): a sessão dev vale só nesta página.
  }
}

// Instância única do Keycloak no módulo: login e logout precisam da mesma
// instância que foi inicializada.
let keycloak: Keycloak | null = null

/**
 * useAuthStore — autenticação opcional via Keycloak.
 *
 * O catálogo público (OPAC) funciona sem sessão; `init()` usa `check-sso` e
 * sempre resolve, autenticado ou não. O login é pedido só nas rotas do balcão
 * (guard do router) ou ao reservar uma obra.
 *
 * Em modo de desenvolvimento (VITE_DEV_AUTH=true) o Keycloak é ignorado e um
 * token fictício com role 'admin' é usado.
 */
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const userName = ref<string | null>(null)

  const isAuthenticated = computed(() => token.value !== null)

  const role = computed<Papel | null>(() => {
    const roles = token.value ? papeisDoToken(token.value) : []
    if (roles.includes('admin')) return 'admin'
    if (roles.includes('operador')) return 'operador'
    if (roles.includes('leitor')) return 'leitor'
    return null
  })

  const isStaff = computed(() => role.value === 'admin' || role.value === 'operador')

  function aplicarSessaoDev(): void {
    token.value = DEV_TOKEN
    userName.value = 'Dev Admin'
  }

  function limparSessao(): void {
    token.value = null
    userName.value = null
  }

  function sincronizarComKeycloak(): void {
    token.value = keycloak?.token ?? null
    userName.value = (keycloak?.tokenParsed as Record<string, unknown> | undefined)?.name as string ?? null
  }

  async function init(): Promise<void> {
    if (IS_DEV_AUTH) {
      if (!IS_DEV_AUTH_ANON || lerSessaoDev()) aplicarSessaoDev()
      return
    }

    const { default: KeycloakJs } = await import('keycloak-js')
    keycloak = new KeycloakJs({
      url: (import.meta.env.VITE_KC_URL as string) || 'http://localhost:8080/auth',
      realm: (import.meta.env.VITE_KC_REALM as string) || 'libsys',
      clientId: (import.meta.env.VITE_KC_CLIENT as string) || 'libsys-spa',
    })
    keycloak.onTokenExpired = () => {
      keycloak
        ?.updateToken(30)
        .then(sincronizarComKeycloak)
        .catch(limparSessao)
    }

    try {
      const authenticated = await keycloak.init({
        onLoad: 'check-sso',
        silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
        pkceMethod: 'S256',
        checkLoginIframe: false,
      })
      if (authenticated) sincronizarComKeycloak()
    } catch (err) {
      // Keycloak fora do ar não pode derrubar o catálogo público: segue como visitante.
      console.warn('Keycloak indisponível; seguindo como visitante.', err)
    }
  }

  async function login(redirectUri?: string): Promise<void> {
    if (IS_DEV_AUTH) {
      gravarSessaoDev(true)
      aplicarSessaoDev()
      if (redirectUri) window.location.assign(redirectUri)
      return
    }
    await keycloak?.login({ redirectUri })
  }

  async function logout(): Promise<void> {
    limparSessao()
    if (IS_DEV_AUTH) {
      gravarSessaoDev(false)
      return
    }
    await keycloak?.logout({ redirectUri: `${window.location.origin}/catalogo` })
  }

  return { token, userName, isAuthenticated, role, isStaff, init, login, logout }
})
