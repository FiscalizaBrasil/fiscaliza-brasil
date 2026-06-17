<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Hero -->
      <section class="bg-gradient-to-br from-chart-2/10 via-background to-primary/10 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold text-foreground sm:text-4xl">Análises Detalhadas</h1>
          <p class="mt-2 text-muted-foreground max-w-2xl">
            Visualizações baseadas em dados reais processados
          </p>
        </div>
      </section>

      <!-- Gastos por Categoria -->
      <section class="py-12 bg-background animate-fade-in-up">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="text-2xl font-bold text-foreground mb-3">Gastos por Categoria</h2>
          <p class="text-muted-foreground mb-8">Distribuição das despesas por tipo de serviço</p>
          <BaseCard v-if="categorias.length">
            <div class="space-y-3 p-6">
              <div v-for="(categoria, index) in categorias" :key="index" class="group">
                <div class="flex items-center justify-between mb-2">
                  <div class="flex-1">
                    <p class="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                      {{ categoria.nome }}
                    </p>
                  </div>
                  <div class="ml-4 text-right">
                    <p class="text-sm font-bold text-foreground">{{ categoria.valor }}</p>
                  </div>
                </div>
                <div class="progress-bar">
                  <div
                    class="progress-fill group-hover:opacity-90"
                    :style="{ width: `${categoria.percentual}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </BaseCard>
          <div v-else class="space-y-4 p-6">
            <div v-for="i in 5" :key="i" class="space-y-2">
              <div class="flex justify-between">
                <div class="skeleton-text" :style="{ width: `${60 + i * 5}%` }"></div>
                <div class="skeleton-text w-20"></div>
              </div>
              <div class="skeleton-rect h-2"></div>
            </div>
          </div>
        </div>
      </section>

      <!-- Evolução Mensal de Gastos -->
      <section class="py-12 bg-muted/30 animate-fade-in-up animate-delay-100">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="text-2xl font-bold text-foreground mb-3">Gastos nos Últimos Meses</h2>
          <p class="text-muted-foreground mb-8">Série temporal dos últimos meses registrados</p>
          <div v-if="mesesGastos.length" class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <BaseCard v-for="mes in mesesGastos" :key="mes.mes" hover>
              <div class="p-6">
                <div class="flex items-start gap-4">
                  <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10">
                    <TrendingUp class="h-6 w-6 text-primary" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-muted-foreground mb-1">{{ mes.titulo }}</p>
                    <p class="text-3xl font-bold text-foreground">{{ mes.valor }}</p>
                  </div>
                </div>
              </div>
            </BaseCard>
          </div>
          <div v-else class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div v-for="i in 3" :key="i" class="card-default p-6">
              <div class="flex items-start gap-4">
                <div class="skeleton-circle h-12 w-12 flex-shrink-0"></div>
                <div class="flex-1 space-y-2">
                  <div class="skeleton-text-sm w-20"></div>
                  <div class="skeleton-text w-24 h-7"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Gastos por Estado -->
      <section class="py-12 bg-background animate-fade-in-up animate-delay-200">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="text-2xl font-bold text-foreground mb-3">Gastos por Estado</h2>
          <p class="text-muted-foreground mb-8">Análise de despesas acumuladas por UF</p>
          <BaseCard v-if="estadosData.length">
            <div class="p-6">
              <div class="max-w-3xl mx-auto">
                <Doughnut :data="chartData" :options="chartOptions" />
              </div>
            </div>
          </BaseCard>
          <div v-else class="flex items-center justify-center h-96">
            <div class="skeleton-circle h-64 w-64"></div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { TrendingUp } from 'lucide-vue-next'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { Doughnut } from 'vue-chartjs'
import BaseCard from '@/components/ui/BaseCard.vue'
import { useCamaraStore } from "@/stores/camara"

ChartJS.register(ArcElement, Tooltip, Legend)

const store = useCamaraStore()

onMounted(() => {
  store.fetchEstatisticasGerais()
})

const categorias = computed(() => {
  if (!store.categorias.length) return []
  
  const maxValor = Math.max(...store.categorias.map(c => c.valor))
  
  return store.categorias.map(c => ({
    nome: c.categoria,
    valor: new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(c.valor),
    percentual: (c.valor / maxValor) * 100
  }))
})

const mesesGastos = computed(() => {
  if (!store.generalStats?.gastos_por_mes) return []
  
  return store.generalStats.gastos_por_mes.map(m => {
    const data = new Date(m.ano, m.mes - 1)
    const mesNome = data.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' })
    const valorFormatado = m.valor >= 1000000 
      ? `R$ ${(m.valor / 1000000).toFixed(1)}M`
      : `R$ ${(m.valor / 1000).toFixed(0)}K`
      
    return {
      mes: `${m.mes}/${m.ano}`,
      titulo: mesNome.charAt(0).toUpperCase() + mesNome.slice(1),
      valor: valorFormatado
    }
  })
})

const estadosData = computed(() => {
  if (!store.generalStats?.gastos_por_estado) return []
  return store.generalStats.gastos_por_estado
})

// Generate colors for all states
const generateColors = (count: number) => {
  const colors = [
    'rgba(59, 130, 246, 0.8)',   // blue
    'rgba(16, 185, 129, 0.8)',   // green
    'rgba(245, 158, 11, 0.8)',   // amber
    'rgba(239, 68, 68, 0.8)',    // red
    'rgba(139, 92, 246, 0.8)',   // purple
    'rgba(236, 72, 153, 0.8)',   // pink
    'rgba(20, 184, 166, 0.8)',   // teal
    'rgba(251, 146, 60, 0.8)',   // orange
    'rgba(34, 197, 94, 0.8)',    // emerald
    'rgba(168, 85, 247, 0.8)',   // violet
  ]
  const result = []
  for (let i = 0; i < count; i++) {
    result.push(colors[i % colors.length])
  }
  return result
}

const chartData = computed(() => ({
  labels: estadosData.value.map(e => e.estado),
  datasets: [
    {
      label: 'Gastos',
      data: estadosData.value.map(e => e.valor),
      backgroundColor: generateColors(estadosData.value.length),
      borderColor: 'rgba(255, 255, 255, 1)',
      borderWidth: 2,
      borderRadius: 4,
    }
  ]
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: true,
  cutout: '70%',
  plugins: {
    legend: {
      position: 'right' as const,
      labels: {
        padding: 15,
        font: {
          size: 12
        },
        generateLabels: (chart: any) => {
          const data = chart.data
          if (data.labels.length && data.datasets.length) {
            return data.labels.map((label: string, i: number) => {
              const value = data.datasets[0].data[i]
              const formattedValue = new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
              }).format(value)
              
              return {
                text: `${label}: ${formattedValue}`,
                fillStyle: data.datasets[0].backgroundColor[i],
                hidden: false,
                index: i
              }
            })
          }
          return []
        }
      }
    },
    tooltip: {
      callbacks: {
        label: function(context: any) {
          const label = context.label || ''
          const value = context.parsed
          const formattedValue = new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
          }).format(value)
          
          // Calculate percentage
          const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0)
          const percentage = ((value / total) * 100).toFixed(1)
          
          return `${label}: ${formattedValue} (${percentage}%)`
        }
      }
    }
  }
}
</script>
