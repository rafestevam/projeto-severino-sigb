import { createRouter, createWebHistory, type RouteMeta } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { PAPEIS_BALCAO, resolverAcesso, rotaInicial } from './guards'

const PUBLICA: RouteMeta = { public: true, layout: 'publico' }
const BALCAO: RouteMeta = { requiresAuth: true, layout: 'balcao', roles: PAPEIS_BALCAO }
const ADMIN: RouteMeta = { requiresAuth: true, layout: 'balcao', roles: ['admin'] }

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: () => rotaInicial(useAuthStore()),
    },
    // ── OPAC (público) ──────────────────────────────────────────────────────
    {
      path: '/catalogo',
      name: 'catalogo',
      component: () => import('@/views/CatalogoView.vue'),
      meta: { ...PUBLICA },
    },
    {
      path: '/catalogo/:id',
      name: 'obra-detalhe',
      component: () => import('@/views/ObraDetalheView.vue'),
      meta: { ...PUBLICA },
    },
    {
      path: '/cadastro',
      name: 'cadastro',
      component: () => import('@/views/CadastroView.vue'),
      meta: { ...PUBLICA },
    },
    // ── Balcão (autenticado) ────────────────────────────────────────────────
    {
      path: '/balcao/checkout',
      name: 'checkout',
      component: () => import('@/views/CheckoutView.vue'),
      meta: { ...BALCAO },
    },
    {
      path: '/balcao/checkin',
      name: 'checkin',
      component: () => import('@/views/CheckinView.vue'),
      meta: { ...BALCAO },
    },
    {
      path: '/catalogacao',
      name: 'catalogacao',
      component: () => import('@/views/CatalogacaoView.vue'),
      meta: { ...BALCAO },
    },
    {
      path: '/inventario',
      name: 'inventario',
      component: () => import('@/views/InventarioView.vue'),
      meta: { ...ADMIN },
    },
    {
      path: '/admin/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { ...ADMIN },
    },
    {
      path: '/:caminho(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach((to) => resolverAcesso(to, useAuthStore()))

export default router
