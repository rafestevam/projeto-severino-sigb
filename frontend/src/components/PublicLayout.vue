<template>
  <div class="public-shell">
    <cds-header aria-label="Biblioteca Severino" class="public-header">
      <router-link to="/catalogo" custom v-slot="{ href, navigate }">
        <cds-header-name :href="href" prefix="📚" @click="navigate">Biblioteca Severino</cds-header-name>
      </router-link>

      <cds-header-nav menu-bar-label="Biblioteca Severino">
        <router-link to="/catalogo" custom v-slot="{ href, navigate, isActive }">
          <cds-header-nav-item :href="href" :is-active="isActive" @click="navigate">
            Catálogo
          </cds-header-nav-item>
        </router-link>
        <router-link v-if="!auth.isAuthenticated" to="/cadastro" custom v-slot="{ href, navigate, isActive }">
          <cds-header-nav-item :href="href" :is-active="isActive" @click="navigate">
            Cadastre-se
          </cds-header-nav-item>
        </router-link>
      </cds-header-nav>

      <div class="header-actions">
        <span v-if="auth.userName" class="header-user">{{ auth.userName }}</span>
        <cds-button v-if="auth.isStaff" kind="ghost" size="sm" @click="router.push('/balcao/checkout')">
          Balcão
        </cds-button>
        <cds-button
          v-if="!auth.isAuthenticated"
          kind="ghost"
          size="sm"
          class="link-cadastro-mobile"
          @click="router.push('/cadastro')"
        >
          Cadastre-se
        </cds-button>
        <cds-button v-if="auth.isAuthenticated" kind="ghost" size="sm" @click="sair">Sair</cds-button>
        <cds-button v-else kind="primary" size="sm" @click="entrar">Entrar</cds-button>
      </div>
    </cds-header>

    <main class="public-content">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import '@carbon/web-components/es/components/ui-shell/index.js'
import '@carbon/web-components/es/components/button/index.js'

const auth = useAuthStore()
const router = useRouter()

function entrar() {
  auth.login(window.location.href)
}

async function sair() {
  await auth.logout()
  router.push('/catalogo')
}
</script>

<style scoped lang="scss">
@use '@carbon/styles/scss/spacing' as *;
@use '@carbon/styles/scss/type' as type;
@use '@carbon/styles/scss/breakpoint' as bp;

.public-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 8000;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: $spacing-03;
  margin-left: auto;
  padding-right: $spacing-05;
  height: 100%;
}

.header-user {
  display: none;
  @include type.type-style('label-01');
  color: var(--cds-text-secondary, #525252);

  @include bp.breakpoint(md) {
    display: inline;
  }
}

// cds-header-nav some abaixo do breakpoint lg; mantém o acesso ao cadastro.
.link-cadastro-mobile {
  @include bp.breakpoint(lg) {
    display: none;
  }
}

.public-content {
  margin-top: $spacing-09; // altura do header (48px)
  padding: $spacing-07 $spacing-05;
  max-width: 1312px;
  margin-inline: auto;
  background: var(--cds-background, #ffffff);
  color: var(--cds-text-primary, #161616);
  min-height: calc(100vh - #{$spacing-09});
}
</style>
