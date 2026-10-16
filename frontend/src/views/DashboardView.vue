<template>
  <div class="dashboard-view">
    <h1 class="page-title">Dashboard de Métricas</h1>

    <div v-if="store.loading" class="loading">Carregando métricas…</div>
    <div v-else-if="store.erro" class="msg-erro">{{ store.erro }}</div>

    <template v-else-if="store.metricas">
      <!-- Cards de totais -->
      <div class="cds--grid cds--grid--narrow grid-section">
        <div class="cds--row">
          <div class="cds--col-sm-2 cds--col-md-4 cds--col-lg-4">
            <div class="card card-stat">
              <div class="card-value">{{ store.metricas.total_obras }}</div>
              <div class="card-label">Obras no acervo</div>
            </div>
          </div>
          <div class="cds--col-sm-2 cds--col-md-4 cds--col-lg-4">
            <div class="card card-stat">
              <div class="card-value">{{ store.metricas.total_exemplares }}</div>
              <div class="card-label">Total de exemplares</div>
            </div>
          </div>
          <div class="cds--col-sm-2 cds--col-md-4 cds--col-lg-4">
            <div class="card card-stat">
              <div class="card-value">{{ store.metricas.total_leitores_ativos }}</div>
              <div class="card-label">Leitores ativos</div>
            </div>
          </div>
          <div class="cds--col-sm-2 cds--col-md-4 cds--col-lg-4">
            <div class="card card-stat">
              <div class="card-value">{{ store.metricas.total_doacoes }}</div>
              <div class="card-label">Doações recebidas</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Exemplares por estado -->
      <section class="card section-card">
        <h2 class="section-title">Exemplares por Estado</h2>
        <div class="cds--grid cds--grid--narrow">
          <div class="cds--row">
            <div class="cds--col-sm-4 cds--col-md-4 cds--col-lg-4">
              <div class="card card-stat card-disponivel">
                <div class="card-value">{{ store.metricas.exemplares_por_estado.disponivel }}</div>
                <div class="card-label">Disponíveis</div>
              </div>
            </div>
            <div class="cds--col-sm-4 cds--col-md-4 cds--col-lg-4">
              <div class="card card-stat card-emprestado">
                <div class="card-value">{{ store.metricas.exemplares_por_estado.emprestado }}</div>
                <div class="card-label">Emprestados</div>
              </div>
            </div>
            <div class="cds--col-sm-4 cds--col-md-4 cds--col-lg-4">
              <div class="card card-stat card-baixado">
                <div class="card-value">{{ store.metricas.exemplares_por_estado.baixado }}</div>
                <div class="card-label">Baixados</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Indicadores de perdas -->
      <section class="card section-card">
        <h2 class="section-title">Indicadores</h2>
        <div class="indicadores">
          <div class="indicador">
            <span class="indicador-label">Taxa de perdas:</span>
            <span class="indicador-valor">
              {{ (store.metricas.taxa_perdas * 100).toFixed(1) }}%
            </span>
          </div>
        </div>
      </section>

      <!-- Top 10 obras mais emprestadas -->
      <section class="card section-card">
        <h2 class="section-title">Top 10 Obras Mais Emprestadas</h2>
        <p v-if="store.metricas.top_obras_emprestadas.length === 0" class="vazio">
          Nenhum dado disponível.
        </p>
        <div v-else class="table-container">
          <table class="cds--data-table cds--data-table--compact">
            <thead>
              <tr>
                <th><span class="cds--table-header-label">#</span></th>
                <th><span class="cds--table-header-label">Título</span></th>
                <th class="align-right"><span class="cds--table-header-label">Empréstimos</span></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(obra, idx) in store.metricas.top_obras_emprestadas"
                :key="obra.obra_id"
              >
                <td class="rank">{{ idx + 1 }}</td>
                <td class="titulo-cell">{{ obra.titulo }}</td>
                <td class="count">{{ obra.total_emprestimos }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'

const store = useDashboardStore()

onMounted(() => {
  store.carregar()
})
</script>

<style scoped lang="scss">
@use '@carbon/styles/scss/spacing' as *;
@use '@carbon/styles/scss/type' as type;

.dashboard-view {
  max-width: 900px;
}

.page-title {
  @include type.type-style('productive-heading-03');
  font-weight: type.font-weight('semibold');
  margin-bottom: $spacing-06;
  color: var(--cds-text-primary, #161616);
}

.loading {
  @include type.type-style('body-long-01');
  color: var(--cds-text-secondary);
  font-style: italic;
  padding: $spacing-07 0;
}

.grid-section {
  padding: 0;
  margin-bottom: $spacing-05;
}

.card {
  background: var(--cds-layer-01, #f4f4f4);
  border: 1px solid var(--cds-border-subtle-01, #e0e0e0);
  padding: $spacing-05;
  margin-bottom: $spacing-05;
}

.section-card {
  border: 1px solid var(--cds-border-subtle-01, #e0e0e0);
  background: var(--cds-layer-01, #f4f4f4);
}

.section-title {
  @include type.type-style('productive-heading-02');
  font-weight: type.font-weight('semibold');
  margin-bottom: $spacing-05;
  color: var(--cds-text-secondary, #525252);
}

.card-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: $spacing-06 $spacing-04;
  margin-bottom: 0;
  min-height: 120px;
  background: var(--cds-layer-02, #ffffff);
}

.card-value {
  @include type.type-style('productive-heading-05');
  font-weight: type.font-weight('semibold');
  color: var(--cds-text-primary, #161616);
}

.card-label {
  @include type.type-style('label-01');
  color: var(--cds-text-secondary, #525252);
  margin-top: $spacing-02;
}

.card-disponivel .card-value {
  color: var(--cds-support-success, #24a148);
}

.card-emprestado .card-value {
  color: var(--cds-support-info, #0f62fe);
}

.card-baixado .card-value {
  color: var(--cds-support-error, #da1e28);
}

.indicadores {
  display: flex;
  flex-direction: column;
  gap: $spacing-03;
}

.indicador {
  display: flex;
  align-items: center;
  gap: $spacing-04;
}

.indicador-label {
  @include type.type-style('body-long-01');
  color: var(--cds-text-secondary, #525252);
}

.indicador-valor {
  @include type.type-style('productive-heading-01');
  font-weight: type.font-weight('semibold');
  color: var(--cds-text-primary, #161616);
}

.table-container {
  width: 100%;
  overflow-x: auto;
}

.align-right {
  text-align: right !important;
}

.titulo-cell {
  @include type.type-style('body-long-01');
}

.rank {
  width: 40px;
  text-align: center;
  color: var(--cds-text-placeholder, #a8a8a8);
}

.count {
  text-align: right;
  font-weight: type.font-weight('semibold');
}

.vazio {
  @include type.type-style('body-long-01');
  color: var(--cds-text-placeholder, #a8a8a8);
}

.msg-erro {
  @include type.type-style('body-long-01');
  color: var(--cds-support-error, #da1e28);
}
</style>
