<template>
  <div class="app-shell">
    <nav class="sidebar">
      <div class="sidebar-header">
        <span class="sidebar-logo">📚 SIGB</span>
        <span class="sidebar-user">{{ auth.userName }}</span>
      </div>

      <ul class="nav-list">
        <li>
          <router-link to="/balcao/checkout" active-class="active">
            Check-Out
          </router-link>
        </li>
        <li>
          <router-link to="/balcao/checkin" active-class="active">
            Check-In
          </router-link>
        </li>
        <li>
          <router-link to="/catalogacao" active-class="active">
            Catalogação
          </router-link>
        </li>
        <li v-if="auth.role === 'admin'">
          <router-link to="/inventario" active-class="active">
            Inventário
          </router-link>
        </li>
        <li v-if="auth.role === 'admin'">
          <router-link to="/admin/dashboard" active-class="active">
            Dashboard
          </router-link>
        </li>
      </ul>

      <div class="sidebar-footer">
        <button class="btn-logout" @click="auth.logout()">Sair</button>
      </div>
    </nav>

    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 220px;
  background: #1c1c1e;
  color: #f5f5f5;
  display: flex;
  flex-direction: column;
  padding: 1rem 0;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.5rem 1rem 1rem;
  border-bottom: 1px solid #333;
}

.sidebar-logo {
  font-size: 1.2rem;
  font-weight: 700;
}

.sidebar-user {
  font-size: 0.8rem;
  color: #aaa;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-list {
  list-style: none;
  margin: 1rem 0 0;
  padding: 0;
  flex: 1;
}

.nav-list li a {
  display: block;
  padding: 0.75rem 1rem;
  color: #ccc;
  text-decoration: none;
  font-size: 0.95rem;
  border-left: 3px solid transparent;
  transition: background 0.15s, border-color 0.15s;
}

.nav-list li a:hover {
  background: #2c2c2e;
  color: #fff;
}

.nav-list li a.active {
  background: #2c2c2e;
  border-left-color: #4a90d9;
  color: #fff;
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid #333;
}

.btn-logout {
  width: 100%;
  padding: 0.5rem;
  background: #c0392b;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-logout:hover {
  background: #e74c3c;
}

.main-content {
  flex: 1;
  padding: 1.5rem;
  background: #f9f9f9;
  overflow-y: auto;
}
</style>
