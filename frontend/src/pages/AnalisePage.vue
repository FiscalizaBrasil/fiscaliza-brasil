<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Hero -->
      <section class="bg-gradient-to-br from-chart-2/10 via-background to-primary/10 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 class="text-3xl font-bold text-foreground sm:text-4xl">Análises Detalhadas</h1>
              <p class="mt-2 text-muted-foreground max-w-2xl">
                Visualizações baseadas em dados reais processados
              </p>
            </div>
            <HeroLegislaturaSelect :store="store" />
          </div>
        </div>
      </section>

      <!-- Evolução de Gastos -->
      <section class="py-12 bg-background animate-fade-in-up">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex items-center justify-between flex-wrap gap-4 mb-8">
            <div>
              <h2 class="text-2xl font-bold text-foreground mb-3">{{ tituloEvolucao }}</h2>
              <p class="text-muted-foreground">{{ descricaoEvolucao }}</p>
            </div>
            <div v-if="opcoesDropdown.length > 0" class="relative">
              <select
                v-model="dropdownSelecionado"
                class="appearance-none bg-background/50 border border-border/50 text-foreground text-sm rounded-lg pl-3 pr-8 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer"
              >
                <option
                  v-for="opt in opcoesDropdown"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </option>
              </select>
              <ChevronDown class="absolute right-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            </div>
          </div>
          <BaseCard v-if="barChartData">
            <div class="p-4 h-80">
              <Bar :data="barChartData" :options="barChartOptions" />
            </div>
          </BaseCard>
          <div v-else class="flex items-center justify-center h-80">
            <div class="skeleton-rect w-full h-64 rounded-xl"></div>
          </div>
        </div>
      </section>

      <!-- Gastos por Categoria -->
      <section class="py-12 bg-muted/30 animate-fade-in-up animate-delay-100">
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

      <!-- Gastos por Estado -->
      <section class="py-12 bg-background animate-fade-in-up animate-delay-200">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="text-2xl font-bold text-foreground mb-3">Gastos por Estado</h2>
          <p class="text-muted-foreground mb-8">Análise de despesas acumuladas por UF</p>
          <BaseCard v-if="estadosData.length">
            <div class="p-6">
              <div class="max-w-3xl mx-auto">
                <Doughnut :data="doughnutChartData" :options="doughnutChartOptions" />
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
import { computed, onMounted, ref, watch } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { Chart as ChartJS, ArcElement, BarElement, CategoryScale, LinearScale, BarController, Tooltip, Legend } from 'chart.js'
import { Doughnut, Bar } from 'vue-chartjs'
import BaseCard from '@/components/ui/BaseCard.vue'
import HeroLegislaturaSelect from '@/components/ui/HeroLegislaturaSelect.vue'
import { useCamaraStore } from "@/stores/camara"
import { formatCurrency } from '@/utils/format'

ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, BarController, Tooltip, Legend)

const store = useCamaraStore()

onMounted(() => {
  store.fetchEstatisticasGerais()
})

const mesesAbrev: Record<number, string> = {
  1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr',
  5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago',
  9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez',
}

// -- Evolução de Gastos (Bar Chart) --

const evolucao = computed(() => store.generalStats?.evolucao_gastos ?? [])

const legislaturaSelecionada = computed(() => store.legislatura)

const isModoMensal = computed(() => legislaturaSelecionada.value !== 0)

const anosDisponiveis = computed(() => {
  const anos = new Set(
    evolucao.value.filter(e => e.mes > 0).map(e => e.ano)
  )
  return Array.from(anos).sort()
})

const legislaturasParaDropdown = computed(() => {
  return store.legislaturasDisponiveis.slice().sort((a: number, b: number) => b - a)
})

const dropdownSelecionado = ref<number>(0)

const tituloEvolucao = computed(() => {
  if (isModoMensal.value) return 'Evolução de Gastos'
  return 'Evolução de Gastos por Ano'
})

const descricaoEvolucao = computed(() => {
  if (isModoMensal.value) return 'Série mensal de gastos da legislatura selecionada'
  return 'Total de gastos agregado por ano'
})

const opcoesDropdown = computed(() => {
  if (isModoMensal.value) {
    return anosDisponiveis.value.map(a => ({ value: a, label: String(a) }))
  }
  const opts = []
  for (const leg of legislaturasParaDropdown.value) {
    const startYear = 2023 - (57 - leg) * 4
    const endYear = startYear + 3
    opts.push({ value: leg, label: `${leg}ª (${startYear}-${endYear})` })
  }
  return opts
})

const formatLegislaturaPeriodo = (legis: number): { start: number; end: number } => {
  const startYear = 2023 - (57 - legis) * 4
  return { start: startYear, end: startYear + 3 }
}

const dadosFiltradosMensal = computed(() => {
  if (!isModoMensal.value) return []
  const ano = dropdownSelecionado.value
  return evolucao.value
    .filter(e => e.ano === ano && e.mes > 0)
    .sort((a, b) => a.mes - b.mes)
})

const dadosFiltradosAnual = computed(() => {
  if (isModoMensal.value) return []
  const legis = dropdownSelecionado.value
  if (legis === 0) {
    return evolucao.value.filter(e => e.mes === 0).sort((a, b) => a.ano - b.ano)
  }
  const { start, end } = formatLegislaturaPeriodo(legis)
  return evolucao.value
    .filter(e => e.mes === 0 && e.ano >= start && e.ano <= end)
    .sort((a, b) => a.ano - b.ano)
})

const barChartData = computed(() => {
  const dados = isModoMensal.value ? dadosFiltradosMensal.value : dadosFiltradosAnual.value
  if (!dados.length) return null

  if (isModoMensal.value) {
    return {
      labels: dados.map(d => mesesAbrev[d.mes] || d.mes),
      datasets: [{
        label: 'Gastos',
        data: dados.map(d => d.valor),
        backgroundColor: 'rgba(34, 139, 34, 0.7)',
        borderColor: 'rgba(34, 139, 34, 1)',
        borderWidth: 1,
        borderRadius: 4,
      }]
    }
  }

  return {
    labels: dados.map(d => String(d.ano)),
    datasets: [{
      label: 'Gastos',
      data: dados.map(d => d.valor),
      backgroundColor: 'rgba(34, 139, 34, 0.7)',
      borderColor: 'rgba(34, 139, 34, 1)',
      borderWidth: 1,
      borderRadius: 4,
    }]
  }
})

const barChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx: any) => formatCurrency(ctx.raw as number)
      }
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: '#888' }
    },
    y: {
      beginAtZero: true,
      grid: { color: 'rgba(0,0,0,0.06)' },
      ticks: {
        color: '#888',
        callback: (val: any) => {
          if (val >= 1_000_000) return `R$ ${(val / 1_000_000).toFixed(1)}M`
          if (val >= 1_000) return `R$ ${(val / 1_000).toFixed(0)}K`
          return `R$ ${val}`
        }
      }
    }
  }
}

watch([anosDisponiveis, isModoMensal], ([anos, mensal]) => {
  if (mensal && anos.length > 0) {
    dropdownSelecionado.value = anos[anos.length - 1]
  }
}, { immediate: true })

watch(isModoMensal, (mensal) => {
  if (!mensal) {
    const legs = legislaturasParaDropdown.value
    dropdownSelecionado.value = legs.length > 0 ? legs[0] : 0
  }
}, { immediate: true })

watch(legislaturaSelecionada, () => {
  store.fetchEstatisticasGerais()
})

// -- Gastos por Categoria --

const categorias = computed(() => {
  if (!store.categorias.length) return []
  
  const maxValor = Math.max(...store.categorias.map(c => c.valor))
  
  return store.categorias.map(c => ({
    nome: c.categoria,
    valor: new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(c.valor),
    percentual: (c.valor / maxValor) * 100
  }))
})

// -- Gastos por Estado (Doughnut) --

const estadosData = computed(() => {
  if (!store.generalStats?.gastos_por_estado) return []
  return store.generalStats.gastos_por_estado
})

const generateColors = (count: number) => {
  const colors = [
    'rgba(59, 130, 246, 0.8)',
    'rgba(16, 185, 129, 0.8)',
    'rgba(245, 158, 11, 0.8)',
    'rgba(239, 68, 68, 0.8)',
    'rgba(139, 92, 246, 0.8)',
    'rgba(236, 72, 153, 0.8)',
    'rgba(20, 184, 166, 0.8)',
    'rgba(251, 146, 60, 0.8)',
    'rgba(34, 197, 94, 0.8)',
    'rgba(168, 85, 247, 0.8)',
  ]
  const result = []
  for (let i = 0; i < count; i++) {
    result.push(colors[i % colors.length])
  }
  return result
}

const doughnutChartData = computed(() => ({
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

const doughnutChartOptions = {
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
          
          const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0)
          const percentage = ((value / total) * 100).toFixed(1)
          
          return `${label}: ${formattedValue} (${percentage}%)`
        }
      }
    }
  }
}
</script>
