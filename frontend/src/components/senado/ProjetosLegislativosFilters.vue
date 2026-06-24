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

      <!-- Search by senador -->
      <div class="relative flex-1">
        <input
          type="text"
          placeholder="Buscar por senador que votou..."
          :value="store.projetosLegislativosFilters.senador"
          @input="onSenadorInput"
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
        <option v-for="tipo in store.tiposUnicosProjetosLegislativos" :key="tipo" :value="tipo">
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

    <!-- Toggle matérias votadas -->
    <div class="flex items-center gap-2 pt-2 border-t border-border/50">
      <button
        @click="store.toggleProjetosLegislativosVotadas()"
        class="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        :class="{ 'text-primary font-medium': store.projetosLegislativosFilters.votadas }"
      >
        <div
          class="w-9 h-5 rounded-full transition-colors relative"
          :class="store.projetosLegislativosFilters.votadas ? 'bg-primary' : 'bg-muted-foreground/30'"
        >
          <div
            class="w-3.5 h-3.5 rounded-full bg-white absolute top-0.5 transition-transform"
            :class="store.projetosLegislativosFilters.votadas ? 'translate-x-[18px]' : 'translate-x-[2px]'"
          />
        </div>
        <span>Apenas matérias com votação</span>
      </button>
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
import { useSenadoStore } from '@/stores/senado'

const store = useSenadoStore()

let searchTimeout: ReturnType<typeof setTimeout> | null = null
let senadorTimeout: ReturnType<typeof setTimeout> | null = null

const onSearchInput = (event: Event) => {
  const value = (event.target as HTMLInputElement).value
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    store.setProjetosLegislativosFilter('search', value)
  }, 500)
}

const onSenadorInput = (event: Event) => {
  const value = (event.target as HTMLInputElement).value
  if (senadorTimeout) clearTimeout(senadorTimeout)
  senadorTimeout = setTimeout(() => {
    store.setProjetosLegislativosFilter('senador', value)
  }, 500)
}

const hasActiveFilters = computed(() => {
  return store.projetosLegislativosFilters.search || store.projetosLegislativosFilters.siglaTipo || store.projetosLegislativosFilters.ano || store.projetosLegislativosFilters.senador || store.projetosLegislativosFilters.votadas
})

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


</script>
