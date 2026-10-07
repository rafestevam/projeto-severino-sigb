import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

/**
 * Instância Axios configurada para a API do Severino SIGB.
 *
 * Interceptor de request: lê o token do useAuthStore e injeta o header
 * Authorization: Bearer {token} em cada requisição.
 */
const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  // O store só estará disponível após a inicialização do Pinia.
  // Este interceptor é chamado em tempo de execução, então é seguro.
  try {
    const auth = useAuthStore()
    if (auth.token) {
      config.headers.Authorization = `Bearer ${auth.token}`
    }
  } catch {
    // Pinia ainda não iniciado (improvável, mas defensivo).
  }
  return config
})

export default api
