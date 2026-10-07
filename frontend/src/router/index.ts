import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/balcao/checkout',
    },
    {
      path: '/balcao/checkout',
      name: 'checkout',
      component: () => import('@/views/CheckoutView.vue'),
    },
    {
      path: '/balcao/checkin',
      name: 'checkin',
      component: () => import('@/views/CheckinView.vue'),
    },
    {
      path: '/catalogacao',
      name: 'catalogacao',
      component: () => import('@/views/CatalogacaoView.vue'),
    },
    {
      path: '/inventario',
      name: 'inventario',
      component: () => import('@/views/InventarioView.vue'),
      meta: { requiresRole: 'admin' },
    },
    {
      path: '/admin/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresRole: 'admin' },
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  const requiredRole = to.meta.requiresRole as string | undefined
  if (requiredRole && auth.role !== requiredRole) {
    // Redireciona para checkout se não tem a role necessária.
    return { name: 'checkout' }
  }
})

export default router
