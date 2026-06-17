<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Hero -->
      <section class="bg-background border-b border-border/50 py-12 border-b border-border/50">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div class="flex items-start gap-4">
              <div class="p-3 rounded-2xl bg-primary-500/10 border border-primary-500/20 hidden sm:block">
                <Building2 class="h-8 w-8 text-primary-600" />
              </div>
              <div>
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-[10px] font-bold text-primary-600 uppercase tracking-widest opacity-70">Senado Federal</span>
                </div>
                <h1 class="text-3xl font-bold text-foreground sm:text-4xl tracking-tight leading-tight">
                  Ranking de Fornecedores do Senado
                </h1>
                <p class="mt-2 text-muted-foreground max-w-2xl text-lg leading-relaxed">
                  Monitore quais empresas recebem recursos da Cota Parlamentar (CEAPS) e fiscalize detalhadamente o destino dessas verbas.
                </p>
              </div>
            </div>

            <!-- Legislatura Selector -->
            <HeroLegislaturaSelect :store="store" />
          </div>
        </div>
      </section>

      <section v-if="error" class="py-4 bg-destructive/10">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <p class="text-sm text-destructive font-medium">Erro ao carregar dados: {{ error }}. Verifique se o backend está rodando em {{ apiUrl }}.</p>
        </div>
      </section>

      <!-- Overview -->
      <section class="py-8 bg-muted/30">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="grid gap-4 sm:grid-cols-3">
            <BaseCard>
              <div class="flex items-center gap-4">
                <div class="p-3 rounded-xl bg-primary/10">
                  <Building2 class="h-6 w-6 text-primary" />
                </div>
                <div v-if="!loading">
                  <p class="text-sm text-muted-foreground">Total de Empresas</p>
                  <p class="text-2xl font-bold text-foreground">{{ formatNumber(stats.total_empresas) }}</p>
                </div>
                <div v-else class="animate-pulse h-10 w-32 bg-muted rounded"></div>
              </div>
            </BaseCard>
            <BaseCard>
              <div class="flex items-center gap-4">
                <div class="p-3 rounded-xl bg-chart-2/10">
                  <Banknote class="h-6 w-6 text-chart-2" />
                </div>
                <div v-if="!loading">
                  <p class="text-sm text-muted-foreground">Total Pago</p>
                  <p class="text-2xl font-bold text-foreground">{{ formatCurrency(stats.total_pago) }}</p>
                </div>
                <div v-else class="animate-pulse h-10 w-32 bg-muted rounded"></div>
              </div>
            </BaseCard>
            <BaseCard>
              <div class="flex items-center gap-4">
                <div class="p-3 rounded-xl bg-chart-3/10">
                  <TrendingUp class="h-6 w-6 text-chart-3" />
                </div>
                <div v-if="!loading">
                  <p class="text-sm text-muted-foreground">Total de Contratos</p>
                  <p class="text-2xl font-bold text-foreground">{{ formatNumber(stats.total_contratos) }}</p>
                </div>
                <div v-else class="animate-pulse h-10 w-32 bg-muted rounded"></div>
              </div>
            </BaseCard>
          </div>
        </div>
      </section>

      <!-- Chart -->
      <section class="py-8">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="text-2xl font-bold text-foreground mb-6">Top 10 Empresas por Valor Recebido</h2>
          <BaseCard v-if="!loading">
            <div class="space-y-4">
              <div v-for="empresa in topEmpresas.slice(0, 10)" :key="empresa.cnpj" class="flex items-center gap-4">
                <div class="w-20 sm:w-32 text-xs sm:text-sm font-medium text-foreground truncate" :title="empresa.nome">{{ empresa.nome }}</div>
                <div class="flex-1 h-8 bg-muted rounded-lg overflow-hidden">
                  <div
                    class="h-full bg-primary rounded-lg flex items-center justify-end px-2 transition-all duration-1000"
                    :style="{ width: `${(empresa.valor_total / (topEmpresas[0]?.valor_total || 1)) * 100}%` }"
                  >
                    <span class="text-xs text-primary-foreground font-medium">{{ formatCurrency(empresa.valor_total) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </BaseCard>
          <div v-else class="space-y-4 animate-pulse">
            <div v-for="i in 10" :key="i" class="h-8 bg-muted rounded"></div>
          </div>
        </div>
      </section>

      <!-- Table -->
      <section class="py-8 bg-muted/30">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 class="text-2xl font-bold text-foreground mb-6">Lista das 20 maiores Empresas</h2>
          <BaseCard v-if="!loading">
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead>
                  <tr class="border-b border-border">
                    <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground">#</th>
                    <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Empresa</th>
                    <th class="text-left py-3 px-4 text-sm font-medium text-muted-foreground hidden md:table-cell">CNPJ/CPF</th>
                    <th class="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Valor Total</th>
                    <th class="text-right py-3 px-4 text-sm font-medium text-muted-foreground hidden sm:table-cell">Contratos</th>
                    <th class="text-right py-3 px-4 text-sm font-medium text-muted-foreground hidden sm:table-cell">% do Total</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(empresa, index) in topEmpresas"
                    :key="empresa.cnpj"
                    class="border-b border-border hover:bg-muted/50 transition-colors"
                  >
                    <td class="py-3 px-4 text-sm text-muted-foreground">{{ empresa.rank || (index + 1) }}</td>
                    <td class="py-3 px-4">
                      <p class="text-sm font-medium text-foreground">{{ empresa.nome }}</p>
                      <p class="text-xs text-muted-foreground">{{ empresa.principais_partidos }}</p>
                    </td>
                    <td class="py-3 px-4 text-sm text-muted-foreground font-mono hidden md:table-cell">{{ empresa.cnpj }}</td>
                    <td class="py-3 px-4 text-sm font-medium text-foreground text-right">{{ formatCurrency(empresa.valor_total) }}</td>
                    <td class="py-3 px-4 text-sm text-muted-foreground text-right hidden sm:table-cell">{{ formatNumber(empresa.contratos) }}</td>
                    <td class="py-3 px-4 text-sm text-muted-foreground text-right hidden sm:table-cell">{{ empresa.percentual?.toFixed(2) }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </BaseCard>
          <div v-else class="animate-pulse space-y-4">
             <div v-for="i in 10" :key="i" class="h-12 bg-muted rounded"></div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Building2, Banknote, TrendingUp } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import HeroLegislaturaSelect from '@/components/ui/HeroLegislaturaSelect.vue'
import { useSenadoStore } from '@/stores/senado'

interface Empresa {
  rank: number
  cnpj: string
  nome: string
  valor_total: number
  contratos: number
  principais_partidos: string
  percentual: number
}

interface Stats {
  total_empresas: number
  total_pago: number
  total_contratos: number
}

const store = useSenadoStore()
const loading = ref(true)
const error = ref<string | null>(null)
const stats = ref<Stats>({
  total_empresas: 0,
  total_pago: 0,
  total_contratos: 0
})
const topEmpresas = ref<Empresa[]>([])

const formatCurrency = (value: number) => {
  if (value >= 1000000) {
    return `R$ ${(value / 1000000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
  }
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

const formatNumber = (value: number) => {
  return value.toLocaleString('pt-BR')
}


const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const fetchStats = async () => {
  loading.value = true
  error.value = null
  try {
    const url = `${apiUrl}/api/senado/${store.legislatura || 0}/empresas/estatisticas`
    const response = await fetch(url)
    
    if (!response.ok) throw new Error(`Erro na API: ${response.status}`)
    
    const data = await response.json()
    
    stats.value = {
      total_empresas: data.total_empresas || 0,
      total_pago: data.total_pago || 0,
      total_contratos: data.total_contratos || 0
    }
    
    if (data.top_20_empresas) {
      topEmpresas.value = data.top_20_empresas.map((e: any) => ({
        rank: e.rank,
        cnpj: e.cnpj || 'N/A',
        nome: e.empresa || 'Desconhecido',
        valor_total: e.valor_total || 0,
        contratos: e.contratos || 0,
        principais_partidos: e.partidos || 'N/A',
        percentual: e.percentual || 0
      }))
    }
  } catch (err: any) {
    console.error('Erro ao buscar dados:', err)
    error.value = err.message || 'Erro de conexão'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStats()
})

watch(() => store.legislatura, () => {
  fetchStats()
})
</script>
