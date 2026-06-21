<template>
  <section class="py-8 bg-muted/30">
    <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <!-- Resumo Principal -->
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <BaseCard>
          <div class="flex items-center gap-4">
            <div class="p-3 rounded-xl bg-primary/10">
              <Users class="h-6 w-6 text-primary" />
            </div>
            <div>
              <p class="text-sm text-muted-foreground">Total de Deputados</p>
              <p class="text-2xl font-bold text-foreground">
                {{ store.deputadoStats?.total_deputados || '...' }}
              </p>
            </div>
          </div>
        </BaseCard>

        <BaseCard>
          <div class="flex items-center gap-4">
            <div class="p-3 rounded-xl bg-accent/10">
              <MapPin class="h-6 w-6 text-accent" />
            </div>
            <div>
              <p class="text-sm text-muted-foreground">Regiões</p>
              <p class="text-2xl font-bold text-foreground">{{ totalRegioes || '...' }}</p>
            </div>
          </div>
        </BaseCard>

        <BaseCard>
          <div class="flex items-center gap-4">
            <div class="p-3 rounded-xl bg-chart-1/10">
              <Flag class="h-6 w-6 text-chart-1" />
            </div>
            <div>
              <p class="text-sm text-muted-foreground">Partidos Ativos</p>
              <p class="text-2xl font-bold text-foreground">
                {{ store.partidosUnicos.length || '...' }}
              </p>
            </div>
          </div>
        </BaseCard>

        <BaseCard>
          <div class="flex items-center gap-4">
            <div class="p-3 rounded-xl bg-chart-2/10">
              <Map class="h-6 w-6 text-chart-2" />
            </div>
            <div>
              <p class="text-sm text-muted-foreground">Estados (UF)</p>
              <p class="text-2xl font-bold text-foreground">{{ totalUfs || '...' }}</p>
            </div>
          </div>
        </BaseCard>
      </div>

      <!-- Evolução de Gastos (full-width) -->
      <BaseCard class="mb-8">
        <template #header>
          <div class="flex items-center justify-between flex-wrap gap-4">
            <h3 class="text-lg font-semibold text-foreground">{{ tituloEvolucao }}</h3>
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
        </template>
        <div v-if="chartData" class="p-4 h-72">
          <Bar :data="chartData" :options="chartOptions" />
        </div>
        <div v-else class="p-8 flex items-center justify-center">
          <BaseLoading message="Carregando evolução de gastos..." />
        </div>
      </BaseCard>

      <div class="grid gap-6 lg:grid-cols-2">
        <!-- Maiores Bancadas -->
        <BaseCard>
          <template #header>
            <h3 class="text-lg font-semibold text-foreground">Maiores Bancadas</h3>
          </template>
          <div v-if="topPartidos.length" class="space-y-3">
            <div v-for="(partido, index) in topPartidos" :key="partido.sigla" class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <span class="text-muted-foreground text-sm w-6">{{ index + 1 }}º</span>
                <span class="font-medium text-foreground">{{ partido.sigla }}</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-24 h-2 bg-muted rounded-full overflow-hidden">
                  <div class="h-full bg-primary rounded-full" :style="{ width: `${(partido.deputados / maxBancada) * 100}%` }" />
                </div>
                <span class="text-sm text-muted-foreground w-8 text-right">{{ partido.deputados }}</span>
              </div>
            </div>
            <div class="pt-2 text-center">
              <p class="text-xs text-muted-foreground">Top 6 partidos com mais deputados</p>
            </div>
          </div>
          <BaseLoading v-else message="Buscando bancadas..." />
        </BaseCard>

        <!-- Distribuição por Região -->
        <BaseCard>
          <template #header>
            <h3 class="text-lg font-semibold text-foreground">Distribuição por Região</h3>
          </template>
          <div v-if="store.deputadoStats?.deputados_por_regiao" class="space-y-4">
            <div v-for="regiao in store.deputadoStats.deputados_por_regiao" :key="regiao.name" class="flex items-center gap-4">
              <div class="flex-1">
                <div class="flex justify-between text-sm mb-1">
                  <span class="text-foreground font-medium">{{ regiao.name }}</span>
                  <span class="text-muted-foreground">{{ regiao.value }} deputados</span>
                </div>
                <div class="h-2 bg-muted rounded-full overflow-hidden">
                  <div 
                    class="h-full rounded-full bg-accent" 
                    :style="{ width: `${(regiao.value / store.deputadoStats.total_deputados) * 100}%` }" 
                  />
                </div>
              </div>
            </div>
          </div>
          <BaseLoading v-else message="Processando regiões..." />
        </BaseCard>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Users, MapPin, Flag, Map, ChevronDown } from 'lucide-vue-next'
import { Chart as ChartJS, BarElement, CategoryScale, LinearScale, BarController, Tooltip, Legend } from 'chart.js'
import { Bar } from 'vue-chartjs'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import { useCamaraStore } from '@/stores/camara'
import { formatCurrency } from '@/utils/format'

ChartJS.register(BarElement, CategoryScale, LinearScale, BarController, Tooltip, Legend)

const store = useCamaraStore()

onMounted(() => {
  store.fetchEstatisticasGerais()
  store.fetchEstatisticasDeputados()
  if (store.deputadosList.length === 0) {
    store.fetchDeputados()
  }
})

const mesesAbrev: Record<number, string> = {
  1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr',
  5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago',
  9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez',
}

const totalRegioes = computed(() => {
  if (store.deputadoStats?.total_regioes !== undefined) return store.deputadoStats.total_regioes
  return store.deputadoStats?.deputados_por_regiao?.length ?? 0
})

const totalUfs = computed(() => {
  if (store.deputadoStats?.total_ufs !== undefined) return store.deputadoStats.total_ufs
  return store.estadosUnicos.length
})

const evolucao = computed(() => store.generalStats?.evolucao_gastos ?? [])

const legislaturaSelecionada = computed(() => store.legislatura)

// Determine mode: mensal (specific legislature) or anual (todas)
const isModoMensal = computed(() => legislaturaSelecionada.value !== 0)

// Years available when in mensal mode (from evolucao data)
const anosDisponiveis = computed(() => {
  const anos = new Set(
    evolucao.value.filter(e => e.mes > 0).map(e => e.ano)
  )
  return Array.from(anos).sort()
})

// For anual mode: available legislatures to filter by
const legislaturasParaDropdown = computed(() => {
  return store.legislaturasDisponiveis.slice().sort((a: number, b: number) => b - a)
})

const dropdownSelecionado = ref<number>(0)

const tituloEvolucao = computed(() => {
  if (isModoMensal.value) {
    return 'Evolução de Gastos'
  }
  return 'Evolução de Gastos por Ano'
})

// Dropdown options
const opcoesDropdown = computed(() => {
  if (isModoMensal.value) {
    return anosDisponiveis.value.map(a => ({ value: a, label: String(a) }))
  }
  // Anual mode: filter by legislature
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

// Filter evolucao data for the monthly chart
const dadosFiltradosMensal = computed(() => {
  if (!isModoMensal.value) return []
  const ano = dropdownSelecionado.value
  return evolucao.value
    .filter(e => e.ano === ano && e.mes > 0)
    .sort((a, b) => a.mes - b.mes)
})

// Filter evolucao data for the anual chart
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

const chartData = computed(() => {
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

const chartOptions = {
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

// Initialize dropdown selection
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

// Reload stats when legislatura changes
watch(legislaturaSelecionada, () => {
  store.fetchEstatisticasGerais()
})

const topPartidos = computed(() => {
  if (!store.deputadosList.length) return []

  const contagem: Record<string, number> = {}
  store.deputadosList.forEach(d => {
    if (d.partido) {
      contagem[d.partido] = (contagem[d.partido] || 0) + 1
    }
  })

  return Object.entries(contagem)
    .map(([sigla, deputados]) => ({ sigla, deputados }))
    .sort((a, b) => b.deputados - a.deputados)
    .slice(0, 6)
})

const maxBancada = computed(() => {
  if (!topPartidos.value.length) return 1
  return topPartidos.value[0].deputados
})
</script>
