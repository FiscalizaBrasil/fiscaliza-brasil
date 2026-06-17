<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Hero -->
      <section class="bg-background border-b border-border/50 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 class="text-3xl font-bold text-foreground sm:text-4xl">Senadores</h1>
              <p class="mt-2 text-muted-foreground max-w-2xl">
                Conheça os senadores da República. Filtre por partido, estado ou região.
              </p>
            </div>
            <HeroLegislaturaSelect :store="store" />
          </div>
        </div>
      </section>

      <!-- Stats -->
      <Stats />

      <!-- Main Content -->
      <section class="py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <Filters />
          <List />
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import Filters from '@/components/senado/Filters.vue'
import List from '@/components/senado/List.vue'
import Stats from '@/components/senado/Stats.vue'
import HeroLegislaturaSelect from '@/components/ui/HeroLegislaturaSelect.vue'
import { useSenadoStore } from '@/stores/senado'

const store = useSenadoStore()
</script>
