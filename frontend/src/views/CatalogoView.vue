<template>
  <div class="catalogo-view">
    <h1 class="page-title">Catálogo da Biblioteca</h1>
    <p class="page-subtitle">Consulte o acervo e veja o que está disponível antes de vir à biblioteca.</p>

    <cds-search
      class="busca"
      size="lg"
      label-text="Buscar no catálogo"
      placeholder="Busque por título, autor ou categoria"
      :value="store.termo"
      @cds-search-input="onBusca"
    ></cds-search>

    <cds-inline-notification
      v-if="store.erro"
      kind="error"
      title="Erro"
      :subtitle="store.erro"
      hide-close-button
      low-contrast
    ></cds-inline-notification>

    <p v-if="store.carregou && !store.erro" class="resumo" aria-live="polite">
      {{ store.total }} {{ store.total === 1 ? 'obra encontrada' : 'obras encontradas' }}
    </p>

    <div v-if="store.carregou && store.itens.length === 0 && !store.loading" class="estado-vazio">
      <h2 class="estado-vazio-titulo">Nenhuma obra encontrada</h2>
      <p>Tente outro termo de busca ou confira a grafia.</p>
    </div>

    <ul class="grid-obras">
      <li v-for="obra in store.itens" :key="obra.id">
        <router-link :to="`/catalogo/${obra.id}`" custom v-slot="{ href, navigate }">
          <cds-clickable-tile :href="href" class="card-obra" @click="navigate">
            <img
              v-if="obra.capa_url"
              :src="obra.capa_url"
              :alt="`Capa de ${obra.titulo}`"
              class="capa"
              loading="lazy"
            />
            <div v-else class="capa capa-placeholder" aria-hidden="true">
              <span>{{ obra.titulo.charAt(0) }}</span>
            </div>
            <h2 class="card-titulo">{{ obra.titulo }}</h2>
            <p class="card-autores">{{ obra.autores.join(', ') }}</p>
            <cds-tag :type="obra.disponivel ? 'green' : 'red'" size="sm">
              {{ obra.disponivel ? 'Disponível' : 'Emprestado' }}
            </cds-tag>
          </cds-clickable-tile>
        </router-link>
      </li>
      <template v-if="store.loading">
        <li v-for="n in 6" :key="`skeleton-${n}`" class="card-skeleton">
          <cds-skeleton-placeholder class="capa"></cds-skeleton-placeholder>
          <cds-skeleton-text heading></cds-skeleton-text>
          <cds-skeleton-text></cds-skeleton-text>
        </li>
      </template>
    </ul>

    <div ref="sentinela" class="sentinela" aria-hidden="true"></div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useCatalogoStore } from '@/stores/catalogo'
import '@carbon/web-components/es/components/search/index.js'
import '@carbon/web-components/es/components/tile/index.js'
import '@carbon/web-components/es/components/tag/index.js'
import '@carbon/web-components/es/components/notification/index.js'
import '@carbon/web-components/es/components/skeleton-placeholder/index.js'
import '@carbon/web-components/es/components/skeleton-text/index.js'

const store = useCatalogoStore()
const sentinela = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

function onBusca(event: Event) {
  store.buscar((event as CustomEvent<{ value: string }>).detail.value)
}

onMounted(() => {
  if (!store.carregou) store.carregarInicial()

  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) store.carregarMais()
    },
    { rootMargin: '200px' },
  )
  if (sentinela.value) observer.observe(sentinela.value)
})

onUnmounted(() => {
  observer?.disconnect()
})
</script>

<style scoped lang="scss">
@use '@carbon/styles/scss/spacing' as *;
@use '@carbon/styles/scss/type' as type;

.page-title {
  @include type.type-style('productive-heading-04');
  color: var(--cds-text-primary, #161616);
  margin-bottom: $spacing-03;
}

.page-subtitle {
  @include type.type-style('body-long-01');
  color: var(--cds-text-secondary, #525252);
  margin-bottom: $spacing-06;
}

.busca {
  margin-bottom: $spacing-05;
}

.resumo {
  @include type.type-style('label-01');
  color: var(--cds-text-secondary, #525252);
  margin-bottom: $spacing-05;
}

.estado-vazio {
  padding: $spacing-09 0;
  text-align: center;
  color: var(--cds-text-secondary, #525252);
}

.estado-vazio-titulo {
  @include type.type-style('productive-heading-03');
  color: var(--cds-text-primary, #161616);
  margin-bottom: $spacing-03;
}

.grid-obras {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
  gap: $spacing-05;
  list-style: none;
  padding: 0;

  > li {
    display: flex;
  }
}

.card-obra,
.card-skeleton {
  flex: 1;
}

.card-skeleton {
  display: flex;
  flex-direction: column;
  gap: $spacing-03;
}

.capa {
  width: 100%;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  margin-bottom: $spacing-03;
}

.capa-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--cds-layer-accent-01, #e0e0e0);
  color: var(--cds-text-secondary, #525252);
  @include type.type-style('productive-heading-06');
}

.card-titulo {
  @include type.type-style('productive-heading-01');
  color: var(--cds-text-primary, #161616);
}

.card-autores {
  @include type.type-style('label-01');
  color: var(--cds-text-secondary, #525252);
  margin-bottom: $spacing-03;
}

.sentinela {
  height: 1px;
}
</style>
