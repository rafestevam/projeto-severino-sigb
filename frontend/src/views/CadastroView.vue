<template>
  <div class="cadastro-view">
    <h1 class="page-title">Quero ser leitor</h1>
    <p class="page-subtitle">
      Faça seu pré-cadastro. Depois é só ir ao balcão com um documento com foto para ativá-lo.
    </p>

    <cds-inline-notification
      v-if="store.sucesso"
      kind="success"
      title="Pré-cadastro recebido!"
      subtitle="Compareça ao balcão da biblioteca com um documento com foto para ativar seu cadastro e começar a pegar livros."
      low-contrast
      hide-close-button
    ></cds-inline-notification>

    <form v-else class="card" novalidate @submit.prevent="store.enviar()">
      <cds-text-input
        label="Nome completo"
        :value="store.form.nome"
        required
        autocomplete="name"
        @input="store.form.nome = valorDe($event)"
      ></cds-text-input>

      <cds-text-input
        label="CPF"
        placeholder="000.000.000-00"
        inputmode="numeric"
        :value="store.form.cpf"
        :invalid="!!store.erroCpf"
        :invalid-text="store.erroCpf ?? ''"
        required
        @input="onCpfInput"
        @focusout="store.form.cpf && store.validarCampoCpf()"
      ></cds-text-input>

      <cds-text-input
        label="Telefone (opcional)"
        placeholder="(00) 00000-0000"
        type="tel"
        autocomplete="tel"
        :value="store.form.telefone"
        @input="store.form.telefone = valorDe($event)"
      ></cds-text-input>

      <cds-text-input
        label="E-mail (opcional)"
        type="email"
        autocomplete="email"
        helper-text="Necessário para reservar livros pelo site."
        :value="store.form.email"
        @input="store.form.email = valorDe($event)"
      ></cds-text-input>

      <cds-inline-notification
        v-if="store.erro"
        kind="error"
        title="Não foi possível cadastrar"
        :subtitle="store.erro"
        low-contrast
        hide-close-button
      ></cds-inline-notification>

      <cds-button
        kind="primary"
        :disabled="store.loading || !store.form.nome.trim() || !store.form.cpf"
        @click="store.enviar()"
      >
        {{ store.loading ? 'Enviando…' : 'Enviar pré-cadastro' }}
      </cds-button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useCadastroStore } from '@/stores/cadastro'
import { formatarCpf } from '@/utils/cpf'
import '@carbon/web-components/es/components/text-input/index.js'
import '@carbon/web-components/es/components/button/index.js'
import '@carbon/web-components/es/components/notification/index.js'

const store = useCadastroStore()

function valorDe(event: Event): string {
  return (event.target as HTMLInputElement).value
}

function onCpfInput(event: Event) {
  store.form.cpf = formatarCpf(valorDe(event))
  if (store.erroCpf) store.validarCampoCpf()
}

onMounted(() => {
  store.resetar()
})
</script>

<style scoped lang="scss">
@use '@carbon/styles/scss/spacing' as *;
@use '@carbon/styles/scss/type' as type;

.cadastro-view {
  max-width: 40rem;
}

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

.card {
  display: flex;
  flex-direction: column;
  gap: $spacing-06;
  background: var(--cds-layer-01, #f4f4f4);
  border: 1px solid var(--cds-border-subtle-01, #e0e0e0);
  padding: $spacing-06;
}
</style>
