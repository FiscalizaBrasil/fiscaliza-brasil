<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Hero -->
      <section class="bg-background border-b border-border/50 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex items-center gap-3 mb-3">
            <div class="p-2 rounded-lg bg-primary-500/15">
              <Receipt class="h-6 w-6 text-primary-500" />
            </div>
            <span class="text-sm font-medium text-primary-500 uppercase tracking-wider">Senado Federal</span>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 class="text-3xl font-bold text-foreground sm:text-4xl">Despesas e Gastos</h1>
              <p class="mt-2 text-muted-foreground max-w-2xl">
                Acompanhe a utilização da cota parlamentar (CEAPS). Totais, rankings e análises por senador.
              </p>
            </div>

            <!-- Legislatura Selector -->
            <HeroLegislaturaSelect :store="store" />
          </div>
        </div>
      </section>

      <section v-if="store.error" class="py-4 bg-destructive/10">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <p class="text-sm text-destructive font-medium">Erro ao carregar dados: {{ store.error }}. Verifique se o backend está rodando em {{ store.apiUrl }}.</p>
        </div>
      </section>

      <!-- Loading state -->
      <BaseLoading v-if="loadingStore.isLoading" :message="loadingStore.message" full-page />

      <template v-else-if="store.generalStats">
        <!-- Overview Cards -->
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


        <!-- Gastos por Partido -->
        <section class="py-8 bg-muted/30">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <h2 class="text-2xl font-bold text-foreground mb-6">Gastos por Partido</h2>

            <div class="grid gap-6 lg:grid-cols-2">
              <!-- Gráfico de pizza -->
              <BaseCard>
                <div class="h-[360px] flex items-center justify-center">
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
                        <p class="text-xs text-muted-foreground">Total Geral</p>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="mt-2 max-h-32 overflow-y-auto">
                  <div class="grid grid-cols-2 gap-2">
                    <div v-for="(partido, index) in gastosPorPartido" :key="partido.partido" class="flex items-center gap-2">
                      <div :class="`w-2 h-2 rounded-full ${getBgColorClass(index)}`" />
                      <span class="text-xs text-muted-foreground truncate">{{ partido.partido }} ({{ partido.percentual }}%)</span>
                    </div>
                  </div>
                </div>
              </BaseCard>

              <!-- Lista de partidos -->
              <div class="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                <BaseCard v-for="(partido, index) in gastosPorPartido" :key="partido.partido" hover class="transition-all">
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

        <!-- Categorias de Despesas -->
        <section class="py-8">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <h2 class="text-2xl font-bold text-foreground mb-6">Gastos por Categoria (CEAPS)</h2>
            <div class="grid gap-4 md:grid-cols-2">
              <BaseCard v-for="categoria in categoriasAgregadas" :key="categoria.nome">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-sm font-medium text-foreground">{{ categoria.nome }}</span>
                  <span class="text-sm text-muted-foreground">{{ categoria.valorFormatado }}</span>
                </div>
                <div class="progress-bar">
                  <div
                    class="progress-fill"
                    :style="{ width: `${categoria.percentual}%` }"
                  />
                </div>
                <p class="text-xs text-muted-foreground mt-1">{{ categoria.percentual.toFixed(1) }}% do total</p>
              </BaseCard>
            </div>
          </div>
        </section>

        <!-- Ranking de Senadores -->
        <section class="py-8 bg-muted/30">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
              <h2 class="text-2xl font-bold text-foreground">Ranking de Senadores</h2>
              <!-- Filtros removidos -->
            </div>

            <div class="space-y-3">
              <BaseCard
                v-for="(senador, index) in senadorsFiltrados"
                :key="senador.id"
                hover
                class="transition-all cursor-pointer"
                @click="goToSenador(senador.id)"
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
                    :src="senador.foto || '/placeholder-user.svg'"
                    :alt="senador.nome"
                    class="h-10 w-10 rounded-full object-cover flex-shrink-0 border-2 border-border"
                    @error="onImgError"
                  />

                  <!-- Info -->
                  <div class="flex-1 min-w-0">
                    <p class="font-semibold text-foreground truncate">{{ senador.nome }}</p>
                    <div class="flex items-center gap-2 mt-0.5">
                      <span class="text-xs px-1.5 py-0.5 rounded bg-primary-500/10 text-primary-600 dark:text-primary-400 font-medium">
                        {{ senador.partido }}
                      </span>
                      <span class="text-xs text-muted-foreground">{{ senador.estado }}</span>
                    </div>
                    <p class="sm:hidden text-sm font-bold text-foreground mt-1">{{ senador.valorFormatado }}</p>
                  </div>

                  <!-- Barra de progresso + valor -->
                  <div class="hidden sm:flex flex-col items-end gap-1 w-40">
                    <span class="text-base font-bold text-foreground">{{ senador.valorFormatado }}</span>
                    <div class="w-full bg-muted rounded-full h-1.5">
                      <div
                        class="h-1.5 rounded-full bg-primary-500"
                        :style="{ width: `${senador.percentualMax}%` }"
                      />
                    </div>
                  </div>

                  <!-- Arrow -->
                  <ChevronRight class="h-4 w-4 text-muted-foreground flex-shrink-0" />
                </div>
              </BaseCard>

              <!-- Empty state -->
              <div v-if="senadorsFiltrados.length === 0" class="text-center py-10 text-muted-foreground">
                Nenhum senador encontrado com os filtros aplicados.
              </div>
            </div>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted} from 'vue'
import { useRouter } from 'vue-router'
import { Banknote, Users, Receipt, ChevronRight } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import HeroLegislaturaSelect from '@/components/ui/HeroLegislaturaSelect.vue'
import { useSenadoStore } from '@/stores/senado'
import { useLoadingStore } from '@/stores/loading'

const store = useSenadoStore()
const loadingStore = useLoadingStore()
const router = useRouter()

onMounted(async () => {
  store.fetchEstatisticasGerais()
})

// ── Gastos por Partido ──────────────────────────────────────────────────────
const gastosPorPartido = computed(() => {
  if (!store.generalStats?.partidos) return []
  const totalGeral = store.generalStats.partidos.reduce((sum, p) => sum + p.total, 0) || 1
  return store.generalStats.partidos.map(p => ({
    partido: p.partido,
    valor: p.total,
    valorFormatado: p.total >= 1000000
      ? `R$ ${(p.total / 1000000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
      : `R$ ${(p.total / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`,
    percentual: ((p.total / totalGeral) * 100).toFixed(1)
  }))
})

const totalGastosFormatado = computed(() => {
  const total = store.generalStats?.total_gastos || 0
  return total >= 1000000 ? `R$ ${(total / 1000000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}M` : `R$ ${(total / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`
})

const allPieSegments = computed(() => {
  if (!gastosPorPartido.value.length) return []
  const circumference = 251.2
  let currentOffset = 0
  return gastosPorPartido.value.map((partido, index) => {
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

// ── Categorias ──────────────────────────────────────────────────────────────
const categoriasAgregadas = computed(() => {
  if (!store.generalStats?.categorias?.length) return []
  const totalCats = store.generalStats.categorias.reduce((s, c) => s + c.total, 0) || 1
  return store.generalStats.categorias.map(c => ({
    nome: c.categoria || 'Não informado',
    total: c.total,
    valorFormatado: c.total >= 1000000
      ? `R$ ${(c.total / 1000000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
      : `R$ ${(c.total / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`,
    percentual: (c.total / totalCats) * 100
  }))
})

// ── Ranking Top 10 ──────────────────────────────────────────────────────────
const senadorsFiltrados = computed(() => {
  const lista = store.generalStats?.top_10 || []
  const maxGasto = lista[0]?.total || 1
  return lista
    .map(s => ({
      ...s,
      id: s.codigo,
      estado: s.uf,
      valorFormatado: s.total >= 1000000
        ? `R$ ${(s.total / 1000000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
        : `R$ ${(s.total / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`,
      percentualMax: (s.total / maxGasto) * 100
    }))
})

// ── Overview Cards ──────────────────────────────────────────────────────────
const overviewStats = computed(() => [
  {
    label: 'Total de Gastos',
    value: store.generalStats
      ? `R$ ${(store.generalStats.total_gastos / 1000000).toFixed(0)}M`
      : '...',
    subvalue: 'Acumulado Total',
    icon: Banknote,
    color: 'text-primary-500',
    bgColor: 'bg-primary-500/10'
  },
  {
    label: 'Média por Senador',
    value: store.generalStats
      ? `R$ ${(store.generalStats.media_por_senador / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`
      : '...',
    icon: Users,
    color: 'text-accent',
    bgColor: 'bg-accent/10'
  },
  {
    label: 'Partidos com Gastos',
    value: store.generalStats
      ? store.generalStats.partidos.length.toString()
      : '...',
    icon: Receipt,
    color: 'text-chart-2',
    bgColor: 'bg-chart-2/10'
  }
])

// ── Helpers ─────────────────────────────────────────────────────────────────
const goToSenador = (id: number) => {
  router.push(`/senado/senadores/${id}`)
}

const onImgError = (e: Event) => {
  const img = e.target as HTMLImageElement
  img.src = '/placeholder-user.svg'
}

const getBgColorClass = (index: number) => {
  const colors = [
    'bg-chart-1', 'bg-chart-2', 'bg-chart-3', 'bg-chart-4', 'bg-chart-5',
    'bg-primary', 'bg-accent', 'bg-red-500', 'bg-blue-500', 'bg-green-500',
    'bg-yellow-500', 'bg-primary-500', 'bg-pink-500', 'bg-indigo-500', 'bg-teal-500',
    'bg-orange-500', 'bg-cyan-500', 'bg-lime-500', 'bg-amber-500', 'bg-emerald-500'
  ]
  return colors[index % colors.length]
}

const getStrokeColorClass = (index: number) => {
  const textColors = [
    'text-chart-1', 'text-chart-2', 'text-chart-3', 'text-chart-4', 'text-chart-5',
    'text-primary', 'text-accent', 'text-red-500', 'text-blue-500', 'text-green-500',
    'text-yellow-500', 'text-primary-500', 'text-pink-500', 'text-indigo-500', 'text-teal-500',
    'text-orange-500', 'text-cyan-500', 'text-lime-500', 'text-amber-500', 'text-emerald-500'
  ]
  return textColors[index % textColors.length]
}
</script>
