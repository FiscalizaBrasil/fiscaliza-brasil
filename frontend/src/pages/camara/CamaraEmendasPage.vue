<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Hero -->
      <section class="bg-gradient-to-br from-accent/10 via-background to-primary/10 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 class="text-3xl font-bold text-foreground sm:text-4xl">Emendas Parlamentares — Câmara</h1>
              <p class="mt-2 text-muted-foreground max-w-2xl">
                Acompanhe a distribuição de emendas parlamentares dos deputados. Rankings por deputado, área e município.
              </p>
            </div>
            <HeroLegislaturaSelect :store="camaraStore" />
          </div>
        </div>
      </section>

      <!-- Overview -->
      <section class="py-12 bg-muted/30">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div v-if="carregando" class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <BaseCard v-for="i in 3" :key="i" class="animate-pulse h-32" />
          </div>
          <div v-else class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <BaseCard class="border-l-4 border-primary">
              <div class="flex items-center gap-4">
                <div class="p-3 rounded-xl bg-primary/10">
                  <Users class="h-6 w-6 text-primary" />
                </div>
                <div>
                  <p class="text-sm font-medium text-muted-foreground uppercase tracking-wider">Deputados com Emendas</p>
                  <p class="text-3xl font-bold text-foreground">{{ estatisticas.totais.deputados }}</p>
                </div>
              </div>
            </BaseCard>
            <BaseCard class="border-l-4 border-accent">
              <div class="flex items-center gap-4">
                <div class="p-3 rounded-xl bg-accent/10">
                  <Landmark class="h-6 w-6 text-accent" />
                </div>
                <div>
                  <p class="text-sm font-medium text-muted-foreground uppercase tracking-wider">Municípios Beneficiados</p>
                  <p class="text-3xl font-bold text-foreground">{{ estatisticas.totais.municipios }}</p>
                </div>
              </div>
            </BaseCard>
            <BaseCard class="border-l-4 border-chart-2 sm:col-span-2 lg:col-span-1">
              <div class="flex items-center gap-4">
                <div class="p-3 rounded-xl bg-chart-2/10">
                  <TrendingUp class="h-6 w-6 text-chart-2" />
                </div>
                <div>
                  <p class="text-sm font-medium text-muted-foreground uppercase tracking-wider">Áreas Contempladas</p>
                  <p class="text-3xl font-bold text-foreground">{{ estatisticas.totais.areas }}</p>
                </div>
              </div>
            </BaseCard>
          </div>
        </div>
      </section>

      <!-- Áreas -->
      <section class="py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex items-center justify-between mb-8">
            <h2 class="text-2xl font-bold text-foreground">Distribuição por Área</h2>
            <span class="text-sm text-muted-foreground">Total: R$ {{ (estatisticas.totais.valor_total / 1000000000).toFixed(1) }} Bi</span>
          </div>
          <div v-if="carregando" class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <BaseCard v-for="i in 6" :key="i" class="animate-pulse h-24" />
          </div>
          <div v-else class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <BaseCard v-for="area in estatisticas.areas" :key="area.nome" class="group bg-card/50 backdrop-blur-sm">
              <div class="flex items-center justify-between mb-3">
                <span class="font-semibold text-foreground group-hover:text-primary transition-colors">{{ area.nome }}</span>
                <span class="text-lg font-bold text-accent">{{ area.percentual }}%</span>
              </div>
              <div class="h-2 bg-muted rounded-full overflow-hidden mb-3">
                <div class="h-full bg-accent rounded-full transition-all duration-1000" :style="{ width: `${area.percentual}%` }" />
              </div>
              <p class="text-sm font-medium text-muted-foreground">R$ {{ (area.valor / 1000000).toFixed(1) }}M</p>
            </BaseCard>
          </div>
        </div>
      </section>

      <!-- Ranking -->
      <section class="py-12 bg-muted/30">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="text-2xl font-bold text-foreground mb-8">Top 10 — Deputados em Emendas</h2>
          <BaseCard class="overflow-hidden border-none shadow-xl">
          <BaseLoading v-if="carregando" message="Carregando ranking..." />
            <div v-else class="divide-y divide-border">
                <div
                  v-for="(deputado, index) in estatisticas.ranking"
                  :key="deputado.id"
                  class="flex items-center gap-3 sm:gap-6 p-3 sm:p-6 hover:bg-muted/50 transition-all duration-300 group cursor-pointer"
                  @click="goToDeputado(deputado.id)"
                >
                  <span class="text-lg sm:text-xl font-black text-muted-foreground/30 w-6 sm:w-8 group-hover:text-primary/50 transition-colors">{{ index + 1 }}º</span>
                <div class="h-10 w-10 sm:h-14 sm:w-14 rounded-xl sm:rounded-2xl bg-muted overflow-hidden border-2 border-primary/20 group-hover:border-primary/50 group-hover:scale-110 transition-all duration-300 shadow-sm flex-shrink-0">
                  <img 
                    :src="deputado.foto || '/placeholder-user.svg'" 
                    :alt="deputado.nome"
                    class="h-full w-full object-cover object-top"
                    @error="($event.target as HTMLImageElement).src = '/placeholder-user.svg'"
                  />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="font-bold text-foreground truncate text-sm sm:text-lg uppercase">{{ deputado.nome }}</p>
                  <p class="text-xs sm:text-sm font-medium text-muted-foreground uppercase tracking-tight">{{ deputado.partido }} • {{ deputado.estado }}</p>
                </div>
                <div class="text-right flex-shrink-0">
                  <p class="text-base sm:text-xl font-extrabold text-accent">R$ {{ (deputado.emendasTotal / 1000000).toFixed(1) }}M</p>
                </div>
              </div>
            </div>
          </BaseCard>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Landmark, Users, TrendingUp } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import HeroLegislaturaSelect from '@/components/ui/HeroLegislaturaSelect.vue'
import { useCamaraStore } from '@/stores/camara'

const estatisticas = ref({
  totais: { deputados: 0, municipios: 0, areas: 0, valor_total: 0 },
  areas: [] as any[],
  ranking: [] as any[]
})

const router = useRouter()
const carregando = ref(true)
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const camaraStore = useCamaraStore()

async function carregarEstatisticas() {
  try {
    const resposta = await fetch(`${API_URL}/api/camara/${camaraStore.legislatura}/emendas/resumo`)
    if (!resposta.ok) throw new Error('Erro ao buscar estatísticas')
    estatisticas.value = await resposta.json()
  } catch (erro) {
    console.error('Falha ao carregar estatísticas:', erro)
  } finally {
    carregando.value = false
  }
}

function goToDeputado(id: number) {
  router.push(`/camara/deputados/${id}`)
}

onMounted(() => {
  carregarEstatisticas()
})

watch(() => camaraStore.legislatura, () => {
  carregando.value = true
  carregarEstatisticas()
})
</script>
