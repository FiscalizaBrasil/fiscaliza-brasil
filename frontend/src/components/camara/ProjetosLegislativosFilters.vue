<template>
  <div class="mb-6 space-y-4">
    <div class="flex flex-col sm:flex-row gap-4">
      <!-- Search by ementa -->
      <div class="relative flex-1">
        <input
          type="text"
          placeholder="Buscar por ementa..."
          :value="store.projetosLegislativosFilters.search"
          @input="onSearchInput"
          class="w-full px-4 py-3 rounded-full border border-gray-300 bg-background text-foreground placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent hover:shadow-md transition-shadow"
        />
      </div>

      <!-- Search by deputado -->
      <div class="relative flex-1">
        <input
          type="text"
          placeholder="Buscar por deputado que votou..."
          :value="store.projetosLegislativosFilters.deputado"
          @input="onDeputadoInput"
          class="w-full px-4 py-3 rounded-full border border-gray-300 bg-background text-foreground placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent hover:shadow-md transition-shadow"
        />
      </div>

      <!-- Tipo -->
      <select
        :value="store.projetosLegislativosFilters.siglaTipo"
        @change="store.setProjetosLegislativosFilter('siglaTipo', ($event.target as HTMLSelectElement).value)"
        class="w-full sm:w-auto px-4 py-3 sm:py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      >
        <option value="">Todos os tipos</option>
        <option v-for="tipo in tiposProjetoLegislativo" :key="tipo" :value="tipo">
          {{ tipo }}
        </option>
      </select>

      <!-- Ano -->
      <select
        :value="store.projetosLegislativosFilters.ano"
        @change="store.setProjetosLegislativosFilter('ano', ($event.target as HTMLSelectElement).value)"
        class="w-full sm:w-auto px-4 py-3 sm:py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      >
        <option value="">Todos os anos</option>
        <option v-for="ano in anosDisponiveis" :key="ano" :value="ano">
          {{ ano }}
        </option>
      </select>
    </div>



    <div v-if="hasActiveFilters" class="flex items-center gap-2">
      <span class="text-sm text-muted-foreground">Filtros ativos:</span>
      <button
        @click="store.resetProjetosLegislativosFilters()"
        class="text-sm text-primary hover:underline"
      >
        Limpar todos
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCamaraStore } from '@/stores/camara'

const store = useCamaraStore()

let searchTimeout: ReturnType<typeof setTimeout> | null = null
let deputadoTimeout: ReturnType<typeof setTimeout> | null = null

const onSearchInput = (event: Event) => {
  const value = (event.target as HTMLInputElement).value
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    store.setProjetosLegislativosFilter('search', value)
  }, 500)
}

const onDeputadoInput = (event: Event) => {
  const value = (event.target as HTMLInputElement).value
  if (deputadoTimeout) clearTimeout(deputadoTimeout)
  deputadoTimeout = setTimeout(() => {
    store.setProjetosLegislativosFilter('deputado', value)
  }, 500)
}

const tiposProjetoLegislativo = computed(() => store.tiposUnicosProjetosLegislativos)

const anosDisponiveis = computed(() => {
  const currentYear = new Date().getFullYear()
  
  let minYear = 2019
  if (store.legislaturasDisponiveis && store.legislaturasDisponiveis.length > 0) {
    const minLegis = Math.min(...store.legislaturasDisponiveis)
    // 57ª Legislatura iniciou em 2023
    minYear = 2023 - (57 - minLegis) * 4
  }

  const anos = []
  for (let i = currentYear; i >= minYear; i--) {
    anos.push(i)
  }
  return anos
})

const hasActiveFilters = computed(() => {
  return store.projetosLegislativosFilters.search || store.projetosLegislativosFilters.siglaTipo || store.projetosLegislativosFilters.ano || store.projetosLegislativosFilters.deputado
})


</script>
