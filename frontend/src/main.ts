import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import './main.scss'

/**
 * Bootstrap da SPA Severino SIGB:
 *  1. Cria a instância do Pinia.
 *  2. Verifica uma sessão SSO existente (check-sso), sem exigir login.
 *  3. Instala o router e monta a aplicação, autenticado ou não.
 *
 * A autenticação é resolvida antes de instalar o router porque a primeira
 * navegação já passa pelo guard: sem isso, quem tem sessão SSO seria mandado
 * de novo ao login ao abrir uma rota do balcão.
 */
async function bootstrap() {
  const app = createApp(App)
  app.use(createPinia())

  await useAuthStore().init()

  app.use(router)
  await router.isReady()
  app.mount('#app')
}

bootstrap()
