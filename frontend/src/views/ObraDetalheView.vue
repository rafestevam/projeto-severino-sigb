<template>
  <div class="obra-detalhe-view">
    <router-link to="/catalogo" custom v-slot="{ href, navigate }">
      <cds-link :href="href" class="voltar" @click="navigate">← Voltar ao catálogo</cds-link>
    </router-link>

    <div v-if="store.loading" class="detalhe">
      <cds-skeleton-placeholder class="capa"></cds-skeleton-placeholder>
      <div class="info">
        <cds-skeleton-text heading></cds-skeleton-text>
        <cds-skeleton-text paragraph :line-count="4"></cds-skeleton-text>
      </div>
    </div>

    <div v-else-if="store.naoEncontrada" class="estado-vazio">
      <h1 class="page-title">Obra não encontrada</h1>
      <p>Ela pode ter sido retirada do acervo.</p>
    </div>

    <cds-inline-notification
      v-else-if="store.erro"
      kind="error"
      title="Erro"
      :subtitle="store.erro"
      hide-close-button
      low-contrast
    ></cds-inline-notification>

    <article v-else-if="store.obra" class="detalhe">
      <img
        v-if="store.obra.capa_url"
        :src="store.obra.capa_url"
        :alt="`Capa de ${store.obra.titulo}`"
        class="capa"
      />
      <div v-else class="capa capa-placeholder" aria-hidden="true">
        <span>{{ store.obra.titulo.charAt(0) }}</span>
      </div>

      <div class="info">
        <div class="tags">
          <cds-tag :type="store.obra.disponivel ? 'green' : 'red'">
            {{ store.obra.disponivel ? 'Disponível' : 'Emprestado' }}
          </cds-tag>
          <cds-tag v-if="preferido" type="purple">
            Preferidos da Galera #{{ store.obra.posicao_ranking }}
          </cds-tag>
          <cds-tag type="cool-gray">{{ store.obra.categoria }}</cds-tag>
        </div>

        <h1 class="page-title">{{ store.obra.titulo }}</h1>
        <p class="autores">{{ store.obra.autores.join(', ') }}</p>
        <p class="publicacao">{{ store.obra.editora }} · {{ store.obra.ano }}</p>

        <dl class="exemplares">
          <div>
            <dt>Disponíveis</dt>
            <dd>{{ store.obra.exemplares_disponiveis }}</dd>
          </div>
          <div>
            <dt>Emprestados</dt>
            <dd>{{ store.obra.exemplares_emprestados }}</dd>
          </div>
        </dl>

        <section v-if="store.obra.sinopse" class="sinopse">
          <h2 class="section-title">Sinopse</h2>
          <p>{{ store.obra.sinopse }}</p>
        </section>

        <div v-if="store.obra.exemplares_disponiveis === 0" class="reserva">
          <p class="reserva-dica">
            Todos os exemplares estão emprestados. Reserve para entrar na fila e ser avisado
            quando um exemplar voltar.
          </p>
          <cds-button kind="primary" :disabled="store.reservando" @click="reservar">
            {{ store.reservando ? 'Reservando…' : 'Reservar' }}
          </cds-button>
        </div>

        <cds-inline-notification
          v-if="store.posicaoFila !== null"
          kind="success"
          title="Reserva confirmada"
          :subtitle="`Você é o nº ${store.posicaoFila} na fila desta obra.`"
          low-contrast
        ></cds-inline-notification>
        <cds-inline-notification
          v-if="store.erroReserva"
          kind="error"
          title="Não foi possível reservar"
          :subtitle="store.erroReserva"
          low-contrast
        ></cds-inline-notification>
      </div>
    </article>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { LIMITE_PREFERIDOS, useObraPublicaStore } from '@/stores/obraPublica'
import '@carbon/web-components/es/components/button/index.js'
import '@carbon/web-components/es/components/link/index.js'
import '@carbon/web-components/es/components/tag/index.js'
import '@carbon/web-components/es/components/notification/index.js'
import '@carbon/web-components/es/components/skeleton-placeholder/index.js'
import '@carbon/web-components/es/components/skeleton-text/index.js'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const store = useObraPublicaStore()

const preferido = computed(() => {
  const posicao = store.obra?.posicao_ranking
  return posicao != null && posicao <= LIMITE_PREFERIDOS
})

function reservar() {
  if (!auth.isAuthenticated) {
    // Volta para esta mesma página após o login e prossegue com a reserva.
    auth.login(`${window.location.origin}/catalogo/${route.params.id}?reservar=1`)
    return
  }
  store.reservar()
}

async function carregar(id: string) {
  store.limparReserva()
  await store.carregar(id)
  if (route.query.reservar === '1') {
    await router.replace({ query: {} })
    if (auth.isAuthenticated && store.obra) await store.reservar()
  }
}

watch(
  () => route.params.id,
  (id) => {
    if (typeof id === 'string') carregar(id)
  },
  { immediate: true },
)
</script>

<style scoped lang="scss">
@use '@carbon/styles/scss/spacing' as *;
@use '@carbon/styles/scss/type' as type;
@use '@carbon/styles/scss/breakpoint' as bp;

.voltar {
  display: inline-block;
  margin-bottom: $spacing-06;
}

.detalhe {
  display: grid;
  grid-template-columns: 1fr;
  gap: $spacing-07;

  @include bp.breakpoint(md) {
    grid-template-columns: minmax(12rem, 18rem) 1fr;
  }
}

.capa {
  width: 100%;
  aspect-ratio: 2 / 3;
  object-fit: cover;
}

.capa-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--cds-layer-accent-01, #e0e0e0);
  color: var(--cds-text-secondary, #525252);
  @include type.type-style('productive-heading-07');
}

.info {
  display: flex;
  flex-direction: column;
  gap: $spacing-04;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-02;
}

.page-title {
  @include type.type-style('productive-heading-05');
  color: var(--cds-text-primary, #161616);
}

.autores {
  @include type.type-style('productive-heading-02');
  color: var(--cds-text-secondary, #525252);
}

.publicacao {
  @include type.type-style('body-long-01');
  color: var(--cds-text-secondary, #525252);
}

.exemplares {
  display: flex;
  gap: $spacing-07;
  padding: $spacing-05 0;
  border-top: 1px solid var(--cds-border-subtle-01, #e0e0e0);
  border-bottom: 1px solid var(--cds-border-subtle-01, #e0e0e0);

  dt {
    @include type.type-style('label-01');
    color: var(--cds-text-secondary, #525252);
  }

  dd {
    @include type.type-style('productive-heading-04');
    color: var(--cds-text-primary, #161616);
  }
}

.section-title {
  @include type.type-style('productive-heading-02');
  margin-bottom: $spacing-03;
  color: var(--cds-text-primary, #161616);
}

.sinopse p {
  @include type.type-style('body-long-02');
  color: var(--cds-text-primary, #161616);
  white-space: pre-line;
}

.reserva {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: $spacing-04;
  margin-top: $spacing-03;
}

.reserva-dica {
  @include type.type-style('body-long-01');
  color: var(--cds-text-secondary, #525252);
}

.estado-vazio {
  padding: $spacing-09 0;
  color: var(--cds-text-secondary, #525252);
}
</style>
