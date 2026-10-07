import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

/**
 * Bootstrap da SPA Severino SIGB:
 *  1. Cria a instância do Pinia.
 *  2. Inicializa o Keycloak via useAuthStore.init().
 *  3. Só monta a aplicação após autenticação bem-sucedida.
 */
async function bootstrap() {
  const app = createApp(App)
  const pinia = createPinia()
  app.use(pinia)
  app.use(router)

  const auth = useAuthStore()
  const authenticated = await auth.init()

  if (authenticated) {
    app.mount('#app')
  }
  // Se não autenticado, o Keycloak redireciona para o login automaticamente.
}

bootstrap()
