<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Hero -->
      <section class="bg-background border-b border-border/50 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 class="text-3xl font-bold text-foreground sm:text-4xl">Projetos Legislativos do Senado</h1>
              <p class="mt-2 text-muted-foreground max-w-2xl">
                Acompanhe os projetos de lei, PECs, medidas provisórias e outros projetos legislativos apresentados no Senado Federal.
              </p>
            </div>
            <HeroLegislaturaSelect :store="store" />
          </div>
        </div>
      </section>
      <BaseLoading v-if="store.loadingProjetosLegislativos" message="Carregando projetos legislativos..." full-page />

      <template v-if="!store.loadingProjetosLegislativos || store.projetosLegislativosList.length > 0">
        <!-- Stats -->
        <ProjetosLegislativosStats />

        <!-- Main content -->
        <section class="py-8">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <ProjetosLegislativosFilters />
            <ProjetosLegislativosList />
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import ProjetosLegislativosFilters from '@/components/senado/ProjetosLegislativosFilters.vue'
import ProjetosLegislativosList from '@/components/senado/ProjetosLegislativosList.vue'
import ProjetosLegislativosStats from '@/components/senado/ProjetosLegislativosStats.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import HeroLegislaturaSelect from '@/components/ui/HeroLegislaturaSelect.vue'
import { useSenadoStore } from '@/stores/senado'

const store = useSenadoStore()

onMounted(() => {
  if (store.projetosLegislativosList.length === 0) {
    store.fetchProjetosLegislativos()
  }
})
</script>
