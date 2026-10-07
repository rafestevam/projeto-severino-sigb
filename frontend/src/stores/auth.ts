import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import Keycloak from 'keycloak-js'

/**
 * useAuthStore — gerencia estado de autenticação Keycloak.
 *
 * - init(): inicializa Keycloak com onLoad: 'login-required'; retorna true se autenticado.
 * - logout(): encerra a sessão e redireciona para o Keycloak.
 * - token: token JWT atual (string) ou null.
 * - role: role extraído do token ('admin' | 'operador' | null).
 * - userName: nome do usuário autenticado.
 */
export const useAuthStore = defineStore('auth', () => {
  const keycloak = new Keycloak({
    url: (import.meta.env.VITE_KC_URL as string) || 'http://localhost:8080/auth',
    realm: (import.meta.env.VITE_KC_REALM as string) || 'libsys',
    clientId: (import.meta.env.VITE_KC_CLIENT as string) || 'libsys-spa',
  })

  const token = ref<string | null>(null)
  const userName = ref<string | null>(null)

  const role = computed<'admin' | 'operador' | null>(() => {
    if (!token.value) return null
    try {
      const payload = JSON.parse(atob(token.value.split('.')[1]))
      const roles: string[] =
        payload?.realm_access?.roles ?? []
      if (roles.includes('admin')) return 'admin'
      if (roles.includes('operador')) return 'operador'
    } catch {
      // token malformado
    }
    return null
  })

  async function init(): Promise<boolean> {
    const authenticated = await keycloak.init({
      onLoad: 'login-required',
      checkLoginIframe: false,
    })
    if (authenticated) {
      token.value = keycloak.token ?? null
      userName.value = (keycloak.tokenParsed as Record<string, unknown>)?.name as string ?? null

      // Renovação automática: se o token expira em menos de 30s, renova.
      setInterval(async () => {
        try {
          const refreshed = await keycloak.updateToken(30)
          if (refreshed) {
            token.value = keycloak.token ?? null
          }
        } catch {
          // falha na renovação — redireciona para login
          await keycloak.login()
        }
      }, 15_000)
    }
    return authenticated
  }

  async function logout(): Promise<void> {
    token.value = null
    userName.value = null
    await keycloak.logout()
  }

  return { token, userName, role, init, logout }
})
