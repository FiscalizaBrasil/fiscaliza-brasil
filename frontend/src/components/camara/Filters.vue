<template>
  <div class="mb-6 space-y-4">
    <div class="flex flex-col sm:flex-row gap-3">
      <!-- Search -->
      <div class="relative flex-1">
        <Search class="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        <input
          type="text"
          placeholder="Buscar deputado..."
          :value="store.filters.search"
          @input="store.setFilter('search', ($event.target as HTMLInputElement).value)"
          class="input-base pl-11 pr-4 py-3 rounded-full"
        />
      </div>

      <!-- Partido -->
      <div class="relative">
        <select
          :value="store.filters.partido"
          @change="store.setFilter('partido', ($event.target as HTMLSelectElement).value)"
          class="input-base px-4 py-2.5 pr-10 rounded-full appearance-none cursor-pointer w-full sm:w-auto sm:min-w-[180px]"
        >
          <option value="">Todos os partidos</option>
          <option v-for="partido in store.partidosUnicos" :key="partido" :value="partido">
            {{ partido }}
          </option>
        </select>
        <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
      </div>

      <!-- Estado -->
      <div class="relative">
        <select
          :value="store.filters.estado"
          @change="store.setFilter('estado', ($event.target as HTMLSelectElement).value)"
          class="input-base px-4 py-2.5 pr-10 rounded-full appearance-none cursor-pointer w-full sm:w-auto sm:min-w-[180px]"
        >
          <option value="">Todos os estados</option>
          <option v-for="estado in store.estadosUnicos" :key="estado" :value="estado">
            {{ estado }}
          </option>
        </select>
        <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
      </div>


    </div>

    <div v-if="hasActiveFilters" class="flex items-center gap-2">
      <span class="text-sm text-muted-foreground">Filtros ativos:</span>
      <button
        @click="store.resetFilters()"
        class="text-sm text-primary hover:text-primary-700 hover:underline font-medium transition-colors"
      >
        Limpar todos
      </button>
    </div>

    <!-- Toggle Suplentes -->
    <div class="flex items-center gap-2 pt-2 border-t border-border/50">
      <button
        @click="store.toggleIncluirSuplentes()"
        class="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        :class="{ 'text-primary font-medium': store.incluirSuplentes }"
      >
        <div
          class="w-9 h-5 rounded-full transition-colors relative"
          :class="store.incluirSuplentes ? 'bg-primary' : 'bg-muted-foreground/30'"
        >
          <div
            class="w-3.5 h-3.5 rounded-full bg-white absolute top-0.5 transition-transform"
            :class="store.incluirSuplentes ? 'translate-x-[18px]' : 'translate-x-[2px]'"
          />
        </div>
        <span>Incluir suplentes</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Search, ChevronDown } from 'lucide-vue-next'
import { useCamaraStore } from '@/stores/camara'

const store = useCamaraStore()

const hasActiveFilters = computed(() => {
  return store.filters.search || store.filters.partido || store.filters.estado
})


</script>
