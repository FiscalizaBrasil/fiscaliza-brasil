<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Hero -->
      <section class="bg-background border-b border-border/50 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 class="text-3xl font-bold text-foreground sm:text-4xl">{{ titulo }}</h1>
              <p class="mt-2 text-muted-foreground max-w-2xl">{{ descricao }}</p>
            </div>
            <HeroLegislaturaSelect :store="store" />
          </div>
        </div>
      </section>

      <BaseLoading
        v-if="store.loadingProjetosLegislativos && store.projetosLegislativosList.length === 0"
        message="Carregando projetos legislativos..."
        full-page
      />

      <div v-show="!store.loadingProjetosLegislativos || store.projetosLegislativosList.length > 0">
        <!-- Stats -->
        <component :is="statsComponent" />

        <!-- Main content -->
        <section class="py-8">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <component :is="filtersComponent" />
            <component :is="listComponent" />
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, defineAsyncComponent } from 'vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import HeroLegislaturaSelect from '@/components/ui/HeroLegislaturaSelect.vue'
import { useCamaraStore } from '@/stores/camara'
import { useSenadoStore } from '@/stores/senado'

const CamaraProjetosLegislativosStats = defineAsyncComponent(() => import('@/components/camara/ProjetosLegislativosStats.vue'))
const SenadoProjetosLegislativosStats = defineAsyncComponent(() => import('@/components/senado/ProjetosLegislativosStats.vue'))
const CamaraProjetosLegislativosFilters = defineAsyncComponent(() => import('@/components/camara/ProjetosLegislativosFilters.vue'))
const SenadoProjetosLegislativosFilters = defineAsyncComponent(() => import('@/components/senado/ProjetosLegislativosFilters.vue'))
const CamaraProjetosLegislativosList = defineAsyncComponent(() => import('@/components/camara/ProjetosLegislativosList.vue'))
const SenadoProjetosLegislativosList = defineAsyncComponent(() => import('@/components/senado/ProjetosLegislativosList.vue'))

const props = defineProps<{
  tipo: 'camara' | 'senado'
}>()

const camaraStore = useCamaraStore()
const senadoStore = useSenadoStore()

const store = computed(() => props.tipo === 'camara' ? camaraStore : senadoStore)

const titulo = computed(() => {
  return props.tipo === 'camara'
    ? 'Projetos Legislativos da Câmara'
    : 'Projetos Legislativos do Senado'
})

const descricao = computed(() => {
  return props.tipo === 'camara'
    ? 'Acompanhe os projetos de lei, PECs, medidas provisórias e outros projetos legislativos apresentados na Câmara dos Deputados.'
    : 'Acompanhe os projetos de lei, PECs, medidas provisórias e outros projetos legislativos apresentados no Senado Federal.'
})

const statsComponent = computed(() => {
  return props.tipo === 'camara'
    ? CamaraProjetosLegislativosStats
    : SenadoProjetosLegislativosStats
})

const filtersComponent = computed(() => {
  return props.tipo === 'camara'
    ? CamaraProjetosLegislativosFilters
    : SenadoProjetosLegislativosFilters
})

const listComponent = computed(() => {
  return props.tipo === 'camara'
    ? CamaraProjetosLegislativosList
    : SenadoProjetosLegislativosList
})

onMounted(() => {
  if (store.value.projetosLegislativosList.length === 0) {
    store.value.fetchProjetosLegislativos()
  }
})
</script>
