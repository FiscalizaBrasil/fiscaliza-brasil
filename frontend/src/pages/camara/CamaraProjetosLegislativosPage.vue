<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Hero -->
      <section class="bg-background border-b border-border/50 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 class="text-3xl font-bold text-foreground sm:text-4xl">Projetos Legislativos da Câmara</h1>
              <p class="mt-2 text-muted-foreground max-w-2xl">
                Acompanhe os projetos de lei, PECs, medidas provisórias e outros projetos legislativos apresentados na Câmara dos Deputados.
              </p>
            </div>
            <HeroLegislaturaSelect :store="store" />
          </div>
        </div>
      </section>
      <BaseLoading v-if="store.loadingProjetosLegislativos && store.projetosLegislativosList.length === 0" message="Carregando projetos legislativos..." full-page />

      <!-- Stats -->
      <ProjetosLegislativosStats />

      <!-- Main content -->
      <section class="py-8">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <ProjetosLegislativosFilters />
          <ProjetosLegislativosList />
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import BaseLoading from '@/components/ui/BaseLoading.vue'
import ProjetosLegislativosFilters from '@/components/camara/ProjetosLegislativosFilters.vue'
import ProjetosLegislativosList from '@/components/camara/ProjetosLegislativosList.vue'
import ProjetosLegislativosStats from '@/components/camara/ProjetosLegislativosStats.vue'
import HeroLegislaturaSelect from '@/components/ui/HeroLegislaturaSelect.vue'
import { useCamaraStore } from '@/stores/camara'

const store = useCamaraStore()
</script>
