<template>
  <section class="py-12 bg-muted/30">
    <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div class="grid grid-cols-2 gap-4 lg:grid-cols-4 lg:gap-6">
        <BaseCard
          v-for="metric in metrics"
          :key="metric.id"
          variant="flat"
          class="hover:border-primary/20"
        >
          <div v-if="loading">
            <div class="animate-pulse flex flex-col gap-2">
              <div class="h-4 w-20 bg-muted rounded"></div>
              <div class="h-8 w-24 bg-muted rounded"></div>
              <div class="h-3 w-16 bg-muted rounded"></div>
            </div>
          </div>
          <div v-else>
            <p class="text-sm text-muted-foreground">{{ metric.label }}</p>
            <p class="mt-1 text-2xl font-bold text-foreground">{{ metric.value }}</p>
            <p class="text-xs text-muted-foreground mt-1">{{ metric.description }}</p>
          </div>
        </BaseCard>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'

const deputadosTotal = ref<number | null>(null)
const senadoresTotal = ref<number | null>(null)
const gastosCamara = ref<number | null>(null)
const gastosSenado = ref<number | null>(null)

const loading = ref(true)

onMounted(async () => {
  const apiUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
  loading.value = true
  
  try {
    const [camaraRes, senadoRes] = await Promise.all([
      fetch(`${apiUrl}/api/camara/resumo-principal?legislatura=0`),
      fetch(`${apiUrl}/api/senado/resumo-principal?legislatura=0`)
    ])
    
    if (camaraRes.ok) {
      const data = await camaraRes.json()
      deputadosTotal.value = data.total_parlamentares
      gastosCamara.value = data.gastos_12_meses
    }
    
    if (senadoRes.ok) {
      const data = await senadoRes.json()
      senadoresTotal.value = data.total_parlamentares
      gastosSenado.value = data.gastos_12_meses
    }
  } catch (err) {
    console.error("Erro ao buscar resumo principal:", err)
  } finally {
    loading.value = false
  }
})

const formatCurrency = (value: number | undefined | null) => {
  if (value === undefined || value === null || isNaN(value)) return "--"
  
  if (value >= 1000000000) {
    return `R$ ${(value / 1000000000).toFixed(1)}B`
  }
  if (value >= 1000000) {
    return `R$ ${(value / 1000000).toFixed(0)}M`
  }
  return `R$ ${(value / 1000).toFixed(0)}K`
}

const metrics = computed(() => [
  {
    id: 1,
    label: "Deputados",
    value: deputadosTotal.value !== null ? deputadosTotal.value : "--",
    description: "Câmara dos Deputados",
  },
  {
    id: 2,
    label: "Senadores",
    value: senadoresTotal.value !== null ? senadoresTotal.value : "--",
    description: "Senado Federal",
  },
  {
    id: 3,
    label: "Gastos Câmara",
    value: formatCurrency(gastosCamara.value),
    description: "Últimos 12 meses",
  },
  {
    id: 4,
    label: "Gastos Senado",
    value: formatCurrency(gastosSenado.value),
    description: "Últimos 12 meses",
  }
])
</script>
