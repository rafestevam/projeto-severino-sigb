import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// Token JWT fictício com role 'admin' no campo realm_access.roles
// Payload: { "sub": "dev-user", "name": "Dev Admin", "realm_access": { "roles": ["admin"] } }
const DEV_TOKEN =
  'eyJhbGciOiJub25lIn0.' +
  btoa(JSON.stringify({ sub: 'dev-user', name: 'Dev Admin', realm_access: { roles: ['admin'] } })) +
  '.'

const IS_DEV_AUTH = import.meta.env.VITE_DEV_AUTH === 'true'

/**
 * useAuthStore — gerencia estado de autenticação Keycloak.
 *
 * Em modo de desenvolvimento (VITE_DEV_AUTH=true) o Keycloak é ignorado e
 * um token fictício com role 'admin' é injetado diretamente.
 */
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const userName = ref<string | null>(null)

  const role = computed<'admin' | 'operador' | null>(() => {
    if (!token.value) return null
    try {
      // O token pode ter padding irregular — usamos replace para lidar com isso
      const base64 = token.value.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
      const payload = JSON.parse(atob(base64))
      const roles: string[] = payload?.realm_access?.roles ?? []
      if (roles.includes('admin')) return 'admin'
      if (roles.includes('operador')) return 'operador'
    } catch {
      // token malformado
    }
    return null
  })

  async function init(): Promise<boolean> {
    if (IS_DEV_AUTH) {
      // Stub: autentica imediatamente sem Keycloak
      token.value = DEV_TOKEN
      userName.value = 'Dev Admin'
      return true
    }

    // Produção: inicializa Keycloak
    const { default: Keycloak } = await import('keycloak-js')
    const keycloak = new Keycloak({
      url: (import.meta.env.VITE_KC_URL as string) || 'http://localhost:8080/auth',
      realm: (import.meta.env.VITE_KC_REALM as string) || 'libsys',
      clientId: (import.meta.env.VITE_KC_CLIENT as string) || 'libsys-spa',
    })

    const authenticated = await keycloak.init({
      onLoad: 'login-required',
      checkLoginIframe: false,
    })

    if (authenticated) {
      token.value = keycloak.token ?? null
      userName.value =
        (keycloak.tokenParsed as Record<string, unknown>)?.name as string ?? null

      setInterval(async () => {
        try {
          const refreshed = await keycloak.updateToken(30)
          if (refreshed) token.value = keycloak.token ?? null
        } catch {
          await keycloak.login()
        }
      }, 15_000)
    }
    return authenticated
  }

  async function logout(): Promise<void> {
    token.value = null
    userName.value = null

    if (!IS_DEV_AUTH) {
      const { default: Keycloak } = await import('keycloak-js')
      const keycloak = new Keycloak({
        url: (import.meta.env.VITE_KC_URL as string) || 'http://localhost:8080/auth',
        realm: (import.meta.env.VITE_KC_REALM as string) || 'libsys',
        clientId: (import.meta.env.VITE_KC_CLIENT as string) || 'libsys-spa',
      })
      await keycloak.logout()
    }
  }

  return { token, userName, role, init, logout }
})
