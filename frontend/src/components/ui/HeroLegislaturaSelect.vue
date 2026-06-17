<template>
  <div class="relative inline-flex items-center gap-3">
    <span class="text-sm font-medium text-foreground/80 hidden sm:inline-block">Legislatura:</span>
    <div class="relative">
      <select
        :value="store.legislatura"
        @change="handleChange"
        class="appearance-none bg-background/50 backdrop-blur-md border border-border/50 text-foreground text-sm font-semibold rounded-full pl-4 pr-10 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary shadow-sm hover:bg-background/80 transition-all cursor-pointer min-w-[200px]"
      >
        <option :value="0">Todas as legislaturas</option>
        <option v-for="leg in store.legislaturasDisponiveis" :key="leg" :value="leg">
          {{ formatLegislatura(leg) }}
        </option>
      </select>
      <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronDown } from 'lucide-vue-next'
import { useLoadingStore } from '@/stores/loading'

const props = defineProps<{
  store: any
}>()

const loadingStore = useLoadingStore()

const formatLegislatura = (legis: number) => {
  if (legis === 0) return 'Todas as legislaturas'
  // 57ª inicia em 2023 e cada legislatura cobre 4 anos corridos (ex.: 2023-2026).
  const startYear = 2023 - (57 - legis) * 4
  const endYear = startYear + 3
  return `${legis}ª (${startYear}-${endYear})`
}

const handleChange = async (event: Event) => {
  const val = Number((event.target as HTMLSelectElement).value)
  if (val === props.store.legislatura) return
  
  loadingStore.startLoading('Atualizando legislatura, aguarde...')
  try {
    await props.store.setLegislatura(val)
  } finally {
    setTimeout(() => {
      loadingStore.stopLoading()
    }, 400) // Small delay to ensure smooth transition
  }
}
</script>
