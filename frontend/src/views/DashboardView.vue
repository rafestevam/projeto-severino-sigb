<template>
  <div class="dashboard-view">
    <h1 class="page-title">Dashboard de Métricas</h1>

    <div v-if="store.loading" class="loading">Carregando métricas…</div>
    <div v-else-if="store.erro" class="msg-erro">{{ store.erro }}</div>

    <template v-else-if="store.metricas">
      <!-- Cards de totais -->
      <div class="cards-grid">
        <div class="card card-stat">
          <div class="card-value">{{ store.metricas.total_obras }}</div>
          <div class="card-label">Obras no acervo</div>
        </div>
        <div class="card card-stat">
          <div class="card-value">{{ store.metricas.total_exemplares }}</div>
          <div class="card-label">Total de exemplares</div>
        </div>
        <div class="card card-stat">
          <div class="card-value">{{ store.metricas.total_leitores_ativos }}</div>
          <div class="card-label">Leitores ativos</div>
        </div>
        <div class="card card-stat">
          <div class="card-value">{{ store.metricas.total_doacoes }}</div>
          <div class="card-label">Doações recebidas</div>
        </div>
      </div>

      <!-- Exemplares por estado -->
      <section class="card">
        <h2>Exemplares por Estado</h2>
        <div class="cards-grid cards-grid-3">
          <div class="card card-stat card-disponivel">
            <div class="card-value">{{ store.metricas.exemplares_por_estado.disponivel }}</div>
            <div class="card-label">Disponíveis</div>
          </div>
          <div class="card card-stat card-emprestado">
            <div class="card-value">{{ store.metricas.exemplares_por_estado.emprestado }}</div>
            <div class="card-label">Emprestados</div>
          </div>
          <div class="card card-stat card-baixado">
            <div class="card-value">{{ store.metricas.exemplares_por_estado.baixado }}</div>
            <div class="card-label">Baixados</div>
          </div>
        </div>
      </section>

      <!-- Indicadores de perdas -->
      <section class="card">
        <h2>Indicadores</h2>
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
      <section class="card">
        <h2>Top 10 Obras Mais Emprestadas</h2>
        <p v-if="store.metricas.top_obras_emprestadas.length === 0" class="vazio">
          Nenhum dado disponível.
        </p>
        <table class="tabela" v-else>
          <thead>
            <tr>
              <th>#</th>
              <th>Título</th>
              <th>Empréstimos</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(obra, idx) in store.metricas.top_obras_emprestadas"
              :key="obra.obra_id"
            >
              <td class="rank">{{ idx + 1 }}</td>
              <td>{{ obra.titulo }}</td>
              <td class="count">{{ obra.total_emprestimos }}</td>
            </tr>
          </tbody>
        </table>
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

<style scoped>
.dashboard-view {
  max-width: 900px;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  color: #1c1c1e;
}

.loading {
  color: #666;
  font-style: italic;
  padding: 2rem 0;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1rem;
}

.cards-grid-3 {
  grid-template-columns: repeat(3, 1fr);
}

.card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.25rem;
  margin-bottom: 1rem;
}

.card h2 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: #555;
}

.card-stat {
  text-align: center;
  padding: 1.25rem 0.75rem;
  margin-bottom: 0;
}

.card-value {
  font-size: 2rem;
  font-weight: 800;
  color: #1c1c1e;
}

.card-label {
  font-size: 0.8rem;
  color: #666;
  margin-top: 0.25rem;
}

.card-disponivel .card-value { color: #27ae60; }
.card-emprestado .card-value { color: #4a90d9; }
.card-baixado .card-value    { color: #c0392b; }

.indicadores {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.indicador {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.95rem;
}

.indicador-label { color: #555; }
.indicador-valor { font-weight: 700; font-size: 1.1rem; color: #1c1c1e; }

.tabela {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.tabela th, .tabela td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e0e0e0;
  text-align: left;
}

.tabela th {
  background: #f5f5f5;
  font-weight: 600;
}

.rank  { width: 40px; text-align: center; color: #888; }
.count { text-align: right; font-weight: 700; }

.vazio { font-size: 0.9rem; color: #888; }

.msg-erro {
  color: #c0392b;
  font-size: 0.9rem;
}
</style>
