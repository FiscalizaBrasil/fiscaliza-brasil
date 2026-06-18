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

      <!-- Stats -->
      <component :is="statsComponent" />

      <!-- Main Content -->
      <section class="py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <component :is="filtersComponent" />
          <component :is="listComponent" />
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import HeroLegislaturaSelect from '@/components/ui/HeroLegislaturaSelect.vue'
import { useCamaraStore } from '@/stores/camara'
import { useSenadoStore } from '@/stores/senado'

const props = defineProps<{
  tipo: 'camara' | 'senado'
}>()

const camaraStore = useCamaraStore()
const senadoStore = useSenadoStore()

const store = computed(() => props.tipo === 'camara' ? camaraStore : senadoStore)

const titulo = computed(() => props.tipo === 'camara' ? 'Deputados' : 'Senadores')
const descricao = computed(() => {
  return props.tipo === 'camara'
    ? 'Conheça todos os deputados. Filtre por partido, estado ou região.'
    : 'Conheça os senadores da República. Filtre por partido, estado ou região.'
})

const statsComponent = computed(() => {
  return props.tipo === 'camara'
    ? defineAsyncComponent(() => import('@/components/camara/Stats.vue'))
    : defineAsyncComponent(() => import('@/components/senado/Stats.vue'))
})

const filtersComponent = computed(() => {
  return props.tipo === 'camara'
    ? defineAsyncComponent(() => import('@/components/camara/Filters.vue'))
    : defineAsyncComponent(() => import('@/components/senado/Filters.vue'))
})

const listComponent = computed(() => {
  return props.tipo === 'camara'
    ? defineAsyncComponent(() => import('@/components/camara/List.vue'))
    : defineAsyncComponent(() => import('@/components/senado/List.vue'))
})
</script>
