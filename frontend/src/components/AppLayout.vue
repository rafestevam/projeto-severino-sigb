<template>
  <div class="app-shell">
    <cds-header class="app-header">
      <cds-header-name href="/" prefix="📚">SIGB - Severino</cds-header-name>
      <div class="header-user-container">
        <span class="header-user">{{ auth.userName }}</span>
      </div>
    </cds-header>

    <cds-side-nav expanded collapse-mode="responsive" class="app-side-nav">
      <cds-side-nav-items>
        <router-link to="/balcao/checkout" custom v-slot="{ href, navigate, isActive }">
          <cds-side-nav-link :href="href" :active="isActive" @click="navigate">
            Check-Out
          </cds-side-nav-link>
        </router-link>

        <router-link to="/balcao/checkin" custom v-slot="{ href, navigate, isActive }">
          <cds-side-nav-link :href="href" :active="isActive" @click="navigate">
            Check-In
          </cds-side-nav-link>
        </router-link>

        <router-link to="/catalogacao" custom v-slot="{ href, navigate, isActive }">
          <cds-side-nav-link :href="href" :active="isActive" @click="navigate">
            Catalogação
          </cds-side-nav-link>
        </router-link>

        <router-link v-if="auth.role === 'admin'" to="/inventario" custom v-slot="{ href, navigate, isActive }">
          <cds-side-nav-link :href="href" :active="isActive" @click="navigate">
            Inventário
          </cds-side-nav-link>
        </router-link>

        <router-link v-if="auth.role === 'admin'" to="/admin/dashboard" custom v-slot="{ href, navigate, isActive }">
          <cds-side-nav-link :href="href" :active="isActive" @click="navigate">
            Dashboard
          </cds-side-nav-link>
        </router-link>
      </cds-side-nav-items>

      <div class="sidebar-footer">
        <cds-button kind="danger" size="md" @click="auth.logout()" class="btn-logout">
          Sair
        </cds-button>
      </div>
    </cds-side-nav>

    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import '@carbon/web-components/es/components/ui-shell/index.js'
import '@carbon/web-components/es/components/button/index.js'

const auth = useAuthStore()
</script>

<style scoped lang="scss">
@use '@carbon/styles/scss/spacing' as *;
@use '@carbon/styles/scss/type' as type;

.app-shell {
  display: flex;
  min-height: 100vh;
}

.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 8000;
}

.header-user-container {
  display: flex;
  align-items: center;
  margin-left: auto;
  padding-right: $spacing-05;
  color: var(--cds-text-inverse, #fff);
  height: 100%;
}

.header-user {
  @include type.type-style('label-01');
  font-weight: type.font-weight('semibold');
}

.app-side-nav {
  position: fixed;
  top: 48px;
  left: 0;
  width: 256px;
  height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
  z-index: 7000;
}

.sidebar-footer {
  margin-top: auto;
  padding: $spacing-05;
  border-top: 1px solid var(--cds-border-subtle-01, #e0e0e0);
}

.btn-logout {
  width: 100%;
}

.main-content {
  flex: 1;
  margin-top: 48px; /* header height */
  margin-left: 256px; /* side-nav width */
  padding: $spacing-06;
  background: var(--cds-background, #ffffff);
  color: var(--cds-text-primary);
  min-height: calc(100vh - 48px);
  overflow-y: auto;
}

@media (max-width: 992px) {
  .app-side-nav {
    display: none;
  }
  .main-content {
    margin-left: 0;
  }
}
</style>
