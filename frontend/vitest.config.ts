import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      include: ['tests/unit/**/*.spec.ts'],
      env: { VITE_DEV_AUTH: 'false', VITE_DEV_AUTH_ANON: 'false' },
    },
  }),
)
