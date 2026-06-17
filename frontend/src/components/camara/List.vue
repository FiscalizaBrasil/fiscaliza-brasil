<template>
  <div>
    <!-- Results count -->
    <p class="text-sm text-muted-foreground mb-4">
      Mostrando {{ store.paginatedDeputados.length }} de {{ store.filteredDeputados.length }} deputados
    </p>

    <!-- Loading State -->
    <BaseLoading v-if="store.loading" message="Carregando deputados..." />

    <!-- Error State -->
    <div v-else-if="store.error" class="text-center py-12">
      <p class="text-destructive">{{ store.error }}</p>
    </div>

    <!-- Grid -->
    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <BaseCard
        v-for="deputado in store.paginatedDeputados"
        :key="deputado.id"
        hover
        class="overflow-hidden"
      >
        <div class="flex items-start gap-4">
          <div class="h-16 w-16 rounded-full border-2 border-border overflow-hidden bg-primary/10 flex items-center justify-center">
            <img
              :src="deputado.foto || '/placeholder-user.svg'"
              :alt="deputado.nome"
              class="w-full h-full object-cover"
              @error="($event.target as HTMLImageElement).src = '/placeholder-user.svg'"
            />
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-foreground truncate">{{ deputado.nome }}</h3>
            <div class="flex items-center gap-2 mt-1">
              <BaseBadge variant="outline">{{ deputado.partido }}</BaseBadge>
              <span class="text-xs text-muted-foreground">{{ deputado.estado }}</span>
            </div>
          </div>
        </div>

        <router-link
          :to="`/camara/deputados/${deputado.id}`"
          class="mt-4 w-full inline-flex items-center justify-center py-2 text-sm font-medium text-primary hover:bg-muted rounded-lg transition-colors group"
        >
          Ver detalhes
          <ArrowRight class="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
        </router-link>
      </BaseCard>
    </div>

    <!-- Empty state -->
    <div v-if="!store.loading && !store.error && store.paginatedDeputados.length === 0" class="text-center py-12">
      <p class="text-muted-foreground">Nenhum deputado encontrado com os filtros selecionados.</p>
    </div>

    <!-- Pagination -->
    <div v-if="store.totalPages > 1" class="flex items-center justify-center gap-2 mt-8">
      <button
        @click="store.setPage(Math.max(1, store.currentPage - 1))"
        :disabled="store.currentPage === 1"
        class="p-2 rounded-lg border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <ChevronLeft class="h-4 w-4" />
      </button>

      <div class="flex items-center gap-1">
        <button
          v-for="page in visiblePages"
          :key="page"
          @click="store.setPage(page)"
          class="h-10 w-10 rounded-lg text-sm font-medium transition-colors"
          :class="store.currentPage === page ? 'bg-primary text-primary-foreground' : 'border border-border hover:bg-muted'"
        >
          {{ page }}
        </button>
      </div>

      <button
        @click="store.setPage(Math.min(store.totalPages, store.currentPage + 1))"
        :disabled="store.currentPage === store.totalPages"
        class="p-2 rounded-lg border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <ChevronRight class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { ArrowRight, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import { useCamaraStore } from '@/stores/camara'

const store = useCamaraStore()

onMounted(() => {
  store.fetchDeputados()
})

const visiblePages = computed(() => {
  const total = store.totalPages
  const current = store.currentPage
  const pages: number[] = []

  if (total <= 5) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else if (current <= 3) {
    for (let i = 1; i <= 5; i++) pages.push(i)
  } else if (current >= total - 2) {
    for (let i = total - 4; i <= total; i++) pages.push(i)
  } else {
    for (let i = current - 2; i <= current + 2; i++) pages.push(i)
  }

  return pages
})
</script>
