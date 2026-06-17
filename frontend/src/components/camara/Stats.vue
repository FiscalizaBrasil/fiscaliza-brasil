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

      <div class="grid gap-6 lg:grid-cols-3">
        <!-- Gastos nos Últimos Meses -->
        <BaseCard>
          <template #header>
            <h3 class="text-lg font-semibold text-foreground">Gastos nos Últimos Meses</h3>
          </template>
          <div v-if="gastosUltimosMeses.length" class="space-y-4">
            <div v-for="mes in gastosUltimosMeses" :key="mes.label" class="flex items-center gap-4">
              <div :class="`w-3 h-3 rounded-full ${mes.color}`" />
              <div class="flex-1">
                <div class="flex justify-between text-sm mb-1">
                  <span class="text-foreground font-medium">{{ mes.label }}</span>
                  <span class="text-muted-foreground">{{ mes.valorFormatado }}</span>
                </div>
                <div class="h-2 bg-muted rounded-full overflow-hidden">
                  <div :class="`h-full rounded-full ${mes.color}`" :style="{ width: `${mes.percentage}%` }" />
                </div>
              </div>
            </div>
          </div>
          <BaseLoading v-else message="Carregando dados..." />
        </BaseCard>

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
import { computed, onMounted } from 'vue'
import { Users, MapPin, Flag, Map } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import { useCamaraStore } from '@/stores/camara'

const store = useCamaraStore()

onMounted(() => {
  store.fetchEstatisticasGerais()
  store.fetchEstatisticasDeputados()
  if (store.deputadosList.length === 0) {
    store.fetchDeputados()
  }
})

const mesesPtBr: Record<number, string> = {
  1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
  5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
  9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro',
}

const chartColors = ['bg-chart-1', 'bg-chart-2', 'bg-chart-3', 'bg-chart-4', 'bg-chart-5']

const totalRegioes = computed(() => {
  if (store.deputadoStats?.total_regioes !== undefined) return store.deputadoStats.total_regioes
  return store.deputadoStats?.deputados_por_regiao?.length ?? 0
})

const totalUfs = computed(() => {
  if (store.deputadoStats?.total_ufs !== undefined) return store.deputadoStats.total_ufs
  return store.estadosUnicos.length
})

const gastosUltimosMeses = computed(() => {
  if (!store.generalStats?.gastos_por_mes) return []

  const ultimos = [...store.generalStats.gastos_por_mes].reverse().slice(0, 5).reverse()
  const maxValor = Math.max(...ultimos.map(m => m.valor), 1)

  return ultimos.map((m, i) => ({
    label: `${mesesPtBr[m.mes] || m.mes} ${m.ano}`,
    valorFormatado: `R$ ${(m.valor / 1000000).toFixed(1)}M`,
    color: chartColors[i % chartColors.length],
    percentage: (m.valor / maxValor) * 100,
  }))
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

