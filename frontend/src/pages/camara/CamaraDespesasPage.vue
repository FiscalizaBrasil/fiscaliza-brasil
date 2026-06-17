<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Hero -->
      <section class="bg-background border-b border-border/50 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex items-center gap-3 mb-3">
            <div class="p-2 rounded-lg bg-primary/15">
              <Banknote class="h-6 w-6 text-primary" />
            </div>
            <div class="flex flex-col">
              <span class="text-sm font-medium text-primary uppercase tracking-wider leading-none">Câmara dos Deputados</span>

            </div>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 class="text-3xl font-bold text-foreground sm:text-4xl">Despesas e Gastos</h1>
              <p class="mt-2 text-muted-foreground max-w-2xl">
                Acompanhe a utilização da cota parlamentar (CEAP). Totais, rankings e análises por deputado.
              </p>
            </div>

            <!-- Legislatura Selector -->
            <HeroLegislaturaSelect :store="store" />
          </div>
        </div>
      </section>

      <BaseLoading v-if="loadingStore.isLoading" :message="loadingStore.message" full-page />

      <template v-else-if="store.generalStats">
        <!-- Overview -->
        <section class="py-8 bg-muted/30">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <BaseCard v-for="stat in overviewStats" :key="stat.label">
                <div class="flex items-center gap-4">
                  <div :class="`p-3 rounded-xl ${stat.bgColor}`">
                    <component :is="stat.icon" :class="`h-6 w-6 ${stat.color}`" />
                  </div>
                  <div>
                    <p class="text-sm text-muted-foreground">{{ stat.label }}</p>
                    <p class="text-2xl font-bold text-foreground">{{ stat.value }}</p>
                    <p v-if="stat.subvalue" class="text-[10px] text-muted-foreground mt-0.5">{{ stat.subvalue }}</p>
                  </div>
                </div>
              </BaseCard>
            </div>
          </div>
        </section>

        <!-- Gráficos e Tabelas -->

      <!-- Gastos por Partido -->
      <section class="py-8">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="text-2xl font-bold text-foreground mb-6">Gastos por Partido</h2>
          
          <div class="grid gap-6 lg:grid-cols-2">
            <!-- Gráfico de pizza com todos os partidos -->
            <BaseCard>
              <div class="h-[400px] flex items-center justify-center">
                <div class="w-56 h-56 relative">
                  <svg viewBox="0 0 100 100" class="transform -rotate-90">
                    <circle 
                      v-for="(segment, index) in allPieSegments" 
                      :key="index"
                      cx="50" 
                      cy="50" 
                      r="40" 
                      fill="none" 
                      stroke="currentColor" 
                      stroke-width="20" 
                      :class="segment.colorClass" 
                      :stroke-dasharray="`${segment.dashArray} 251.2`"
                      :stroke-dashoffset="segment.dashOffset"
                    />
                  </svg>
                  <div class="absolute inset-0 flex items-center justify-center">
                    <div class="text-center">
                      <p class="text-2xl font-bold text-foreground">{{ totalGastosFormatado }}</p>
                      <p class="text-xs text-muted-foreground">Total</p>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mt-4 max-h-32 overflow-y-auto">
                <div class="grid grid-cols-2 gap-2">
                  <div v-for="(partido, index) in todosPartidos.slice(0, 10)" :key="partido.partido" class="flex items-center gap-2">
                    <div :class="`w-2 h-2 rounded-full ${getBgColorClass(index)}`" />
                    <span class="text-xs text-muted-foreground truncate">{{ partido.partido }} ({{ partido.percentual }}%)</span>
                  </div>
                </div>
              </div>
            </BaseCard>

            <!-- Lista de todos os partidos -->
            <div class="space-y-3 max-h-[500px] overflow-y-auto pr-2">
              <BaseCard v-for="(partido, index) in todosPartidos" :key="partido.partido" hover class="transition-all">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3 flex-1">
                    <div :class="`w-3 h-10 rounded ${getBgColorClass(index)}`" />
                    <div class="flex-1 min-w-0">
                      <h3 class="font-semibold text-foreground truncate">{{ partido.partido }}</h3>
                      <p class="text-xs text-muted-foreground">{{ partido.percentual }}% do total</p>
                    </div>
                  </div>
                  <p class="text-lg font-bold text-foreground ml-2">{{ partido.valorFormatado }}</p>
                </div>
              </BaseCard>
            </div>
          </div>
        </div>
      </section>

      <!-- Categorias -->
      <section class="py-8 bg-muted/30">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="text-2xl font-bold text-foreground mb-6">Gastos por Categoria</h2>
          <div class="grid gap-4 md:grid-cols-2">
            <BaseCard v-for="categoria in categoriasDespesas" :key="categoria.nome">
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm font-medium text-foreground">{{ categoria.nome }}</span>
                <span class="text-sm text-muted-foreground">R$ {{ (categoria.total / 1000000).toFixed(1) }}M</span>
              </div>
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: `${categoria.percentual}%` }"
                />
              </div>
            </BaseCard>
          </div>
        </div>
      </section>

      <!-- Ranking de Deputados -->
      <section class="py-8">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
            <h2 class="text-2xl font-bold text-foreground">Ranking de Deputados</h2>
              <!-- Filtros removidos -->
          </div>

          <div class="space-y-3">
            <BaseCard
              v-for="(dep, index) in deputadosFiltrados"
              :key="dep.id"
              hover
              class="transition-all cursor-pointer"
              @click="goToDeputado(dep.id)"
            >
              <div class="flex items-center gap-4">
                <!-- Posição com Medalha -->
                <div v-if="index < 3" class="flex-shrink-0 w-10 h-10 flex items-center justify-center text-2xl">
                  {{ index === 0 ? '🥇' : index === 1 ? '🥈' : '🥉' }}
                </div>
                <div v-else class="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm bg-muted text-muted-foreground">
                  {{ index + 1 }}°
                </div>

                <!-- Foto -->
                <img
                  :src="`https://www.camara.leg.br/internet/deputado/bandep/${dep.id}.jpg` || '/placeholder-user.svg'"
                  :alt="dep.nome"
                  class="h-10 w-10 rounded-full object-cover flex-shrink-0 border-2 border-border"
                  @error="onImgError"
                />

                <!-- Info -->
                <div class="flex-1 min-w-0">
                  <p class="font-semibold text-foreground truncate">{{ dep.nome }}</p>
                  <div class="flex items-center gap-2 mt-0.5">
                    <span class="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium">
                      {{ dep.partido }}
                    </span>
                    <span class="text-xs text-muted-foreground">{{ dep.estado }}</span>
                  </div>
                  <p class="sm:hidden text-sm font-bold text-foreground mt-1">{{ dep.valorFormatado }}</p>
                </div>

                <!-- Barra de progresso + valor -->
                <div class="hidden sm:flex flex-col items-end gap-1 w-40">
                  <span class="text-base font-bold text-foreground">{{ dep.valorFormatado }}</span>
                  <div class="w-full bg-muted rounded-full h-1.5">
                    <div
                      class="h-1.5 rounded-full bg-primary"
                      :style="{ width: `${dep.percentualMax}%` }"
                    />
                  </div>
                </div>

                <!-- Arrow -->
                <ChevronRight class="h-4 w-4 text-muted-foreground flex-shrink-0" />
              </div>
            </BaseCard>

            <!-- Empty state -->
            <div v-if="deputadosFiltrados.length === 0" class="text-center py-10 text-muted-foreground">
              Nenhum deputado encontrado com os filtros aplicados.
            </div>
          </div>
        </div>
      </section>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { Banknote, Users, Building2, ChevronRight } from 'lucide-vue-next'
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import HeroLegislaturaSelect from '@/components/ui/HeroLegislaturaSelect.vue'
import { useCamaraStore } from "@/stores/camara"
import { useLoadingStore } from "@/stores/loading"

const store = useCamaraStore()
const loadingStore = useLoadingStore()
const router = useRouter()

onMounted(async () => {
  loadingStore.startLoading('Carregando estatísticas da Câmara...')
  await Promise.allSettled([
    store.fetchEstatisticasGerais(),
    store.fetchEstatisticasDeputados()
  ])
  loadingStore.stopLoading()
  
  if (store.deputadosList.length === 0) {
    store.fetchDeputados()
  }
})

const todosPartidos = computed(() => {
  if (!store.generalStats?.gastos_por_partido) return []
  
  const totalGeral = store.generalStats.gastos_por_partido.reduce((sum, p) => sum + p.valor, 0)
  
  return store.generalStats.gastos_por_partido.map(p => ({
    partido: p.partido,
    valor: p.valor,
    valorFormatado: p.valor >= 1000000 
      ? `R$ ${(p.valor / 1000000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
      : `R$ ${(p.valor / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`,
    percentual: ((p.valor / totalGeral) * 100).toFixed(1)
  }))
})

const allPieSegments = computed(() => {
  if (!todosPartidos.value.length) return []
  
  const circumference = 251.2
  let currentOffset = 0
  
  return todosPartidos.value.map((partido, index) => {
    const percentage = parseFloat(partido.percentual)
    const dashArray = (percentage / 100) * circumference
    const segment = {
      colorClass: getStrokeColorClass(index),
      dashArray: dashArray.toFixed(1),
      dashOffset: -currentOffset
    }
    currentOffset += dashArray
    return segment
  })
})

const getBgColorClass = (index: number) => {
  const colors = [
    'bg-chart-1', 'bg-chart-2', 'bg-chart-3', 'bg-chart-4', 'bg-chart-5',
    'bg-primary', 'bg-accent', 'bg-red-500', 'bg-blue-500', 'bg-green-500',
    'bg-yellow-500', 'bg-purple-500', 'bg-pink-500', 'bg-indigo-500', 'bg-teal-500',
    'bg-orange-500', 'bg-cyan-500', 'bg-lime-500', 'bg-amber-500', 'bg-emerald-500'
  ]
  return colors[index % colors.length]
}

const getStrokeColorClass = (index: number) => {
  const textColors = [
    'text-chart-1', 'text-chart-2', 'text-chart-3', 'text-chart-4', 'text-chart-5',
    'text-primary', 'text-accent', 'text-red-500', 'text-blue-500', 'text-green-500',
    'text-yellow-500', 'text-purple-500', 'text-pink-500', 'text-indigo-500', 'text-teal-500',
    'text-orange-500', 'text-cyan-500', 'text-lime-500', 'text-amber-500', 'text-emerald-500'
  ]
  return textColors[index % textColors.length]
}

const totalGastosFormatado = computed(() => {
  if (!store.generalStats?.gastos_por_partido) return 'R$ 0'
  const total = store.generalStats.gastos_por_partido.reduce((sum, p) => sum + p.valor, 0)
  return `R$ ${(total / 1000000).toFixed(0)}M`
})

const categoriasDespesas = computed(() => {
  if (!store.generalStats?.gastos_por_categoria) return []
  
  const maxValor = Math.max(...store.generalStats.gastos_por_categoria.map(c => c.valor))
  
  return store.generalStats.gastos_por_categoria.map(c => ({
    nome: c.categoria,
    total: c.valor,
    percentual: (c.valor / maxValor) * 100
  }))
})

// Ranking de deputados por gasto
const deputadosComGasto = computed(() => {
  if (!store.generalStats?.gastos_deputados) return []
  return store.generalStats.gastos_deputados.map(dep => ({
    id: dep.deputado_id,
    nome: dep.nome_civil,
    partido: dep.sigla_partido,
    estado: dep.estado,
    totalGasto: dep.total_gasto
  }))
})

const deputadosFiltrados = computed(() => {
  const maxGasto = deputadosComGasto.value[0]?.totalGasto || 1
  return deputadosComGasto.value
    .map(d => ({
      ...d,
      valorFormatado: d.totalGasto >= 1000000
        ? `R$ ${(d.totalGasto / 1000000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
        : `R$ ${(d.totalGasto / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`,
      percentualMax: (d.totalGasto / maxGasto) * 100
    }))
})

const goToDeputado = (id: number) => {
  router.push(`/camara/deputados/${id}`)
}

const onImgError = (e: Event) => {
  const img = e.target as HTMLImageElement
  img.src = '/placeholder-user.svg'
}

const overviewStats = computed(() => [
  { 
    label: "Total de Gastos", 
    value: store.generalStats 
      ? `R$ ${(store.generalStats.total_gastos / 1000000).toFixed(0)}M` 
      : "...", 
    subvalue: "Acumulado Total",
    icon: Banknote, 
    color: "text-primary", 
    bgColor: "bg-primary/10" 
  },
  { 
    label: "Média por Deputado", 
    value: store.generalStats && store.deputadoStats && store.deputadoStats.total_deputados > 0
      ? `R$ ${(store.generalStats.total_gastos / store.deputadoStats.total_deputados / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`
      : "...", 
    icon: Users, 
    color: "text-accent", 
    bgColor: "bg-accent/10" 
  },
  { 
    label: "Empresas Contratadas", 
    value: store.generalStats 
      ? store.generalStats.total_empresas_contratadas.toLocaleString()
      : "...", 
    icon: Building2, 
    color: "text-chart-2", 
    bgColor: "bg-chart-2/10" 
  },
])
</script>
