<template>
  <component :is="layout">
    <router-view />
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import PublicLayout from '@/components/PublicLayout.vue'

const route = useRoute()
const layout = computed(() => (route.meta.layout === 'publico' ? PublicLayout : AppLayout))
</script>
