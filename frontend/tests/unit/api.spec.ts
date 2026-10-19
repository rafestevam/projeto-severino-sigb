import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { InternalAxiosRequestConfig } from 'axios'
import { AxiosHeaders } from 'axios'
import api from '@/services/api'
import { useAuthStore } from '@/stores/auth'

type Interceptor = (config: InternalAxiosRequestConfig) => InternalAxiosRequestConfig

function aplicarInterceptor(): InternalAxiosRequestConfig {
  const handlers = (api.interceptors.request as unknown as { handlers: { fulfilled: Interceptor }[] }).handlers
  return handlers[0].fulfilled({ headers: new AxiosHeaders() } as InternalAxiosRequestConfig)
}

describe('api interceptor', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('não envia Authorization para visitante anônimo', () => {
    expect(aplicarInterceptor().headers.Authorization).toBeUndefined()
  })

  it('envia Bearer quando há token', () => {
    useAuthStore().token = 'abc'
    expect(aplicarInterceptor().headers.Authorization).toBe('Bearer abc')
  })
})
