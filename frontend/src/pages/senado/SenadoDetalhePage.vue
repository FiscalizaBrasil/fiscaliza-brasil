<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Breadcrumb -->
      <div class="bg-muted/30 border-b border-border">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <router-link to="/senado/senadores" class="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
            <ChevronLeft class="h-4 w-4" />
            Voltar para lista
          </router-link>

          <!-- Legislatura Selector -->
          <div class="flex items-center gap-3 bg-neutral-50 px-3 py-1.5 rounded-full border border-neutral-200">
            <span class="text-xs font-bold text-neutral-500 uppercase tracking-wider">Visualizando:</span>
            <select
              :value="store.legislatura"
              @change="store.setLegislatura(Number(($event.target as HTMLSelectElement).value))"
              class="text-sm font-bold text-neutral-800 bg-transparent border-none p-0 focus:ring-0 cursor-pointer"
            >
              <template v-if="store.currentSenador?.legislaturas_ativas?.length">
                <option :value="0">Todas as legislaturas (Histórico)</option>
                <option v-for="legis in store.currentSenador.legislaturas_ativas" :key="legis" :value="legis">
                  {{ formatLegislatura(legis) }}
                </option>
              </template>
              <template v-else>
                <option :value="57">57ª Legislatura (2023-2026)</option>
                <option :value="56">56ª Legislatura (2019-2022)</option>
                <option :value="55">55ª Legislatura (2015-2018)</option>
              </template>
            </select>
          </div>
        </div>
      </div>

      <BaseLoading v-if="store.loadingDetail" message="Carregando detalhes do senador..." full-page />

      <div v-else-if="store.error" class="flex-1 flex items-center justify-center min-h-[400px]">
        <p class="text-destructive">{{ store.error }}</p>
      </div>

      <template v-else-if="store.currentSenador">
        <!-- Profile -->
        <section class="py-8 bg-background border-b border-border/50">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div class="flex flex-col lg:flex-row gap-8">
              <!-- Profile card -->
              <BaseCard class="lg:w-80 flex-shrink-0 border-primary-100">
                <div class="text-center">
                  <div class="h-32 w-32 mx-auto rounded-full border-4 border-primary-200 overflow-hidden bg-primary-50 flex items-center justify-center">
                    <img
                      :src="store.currentSenador.foto || '/placeholder-user.svg'"
                      :alt="store.currentSenador.nome_civil"
                      class="w-full h-full object-cover"
                      @error="($event.target as HTMLImageElement).src = '/placeholder-user.svg'"
                    />
                  </div>

                  <h1 class="mt-4 text-xl font-bold text-foreground">{{ store.currentSenador.nome_civil }}</h1>

                  <div class="mt-2 flex flex-wrap items-center justify-center gap-2">
                    <BaseBadge variant="outline">Partido: {{ store.currentSenador.sigla_partido }}</BaseBadge>
                    <BaseBadge v-if="store.currentSenador.uf" variant="outline">Estado: {{ store.currentSenador.uf }}</BaseBadge>
                  </div>

                  <div class="mt-6 space-y-3 text-sm text-left">
                    <div class="flex flex-col gap-1">
                      <div class="flex items-center gap-2 text-muted-foreground">
                        <Mail class="h-4 w-4 text-primary-500" />
                        <span class="text-xs font-bold uppercase tracking-wider">E-mail</span>
                      </div>
                      <span class="truncate pl-6">{{ store.currentSenador.email || 'Indisponível' }}</span>
                    </div>

                    <div class="flex flex-col gap-1">
                      <div class="flex items-center gap-2 text-muted-foreground">
                        <Calendar class="h-4 w-4 text-primary-500" />
                        <span class="text-xs font-bold uppercase tracking-wider">Nascimento</span>
                      </div>
                      <span class="pl-6">{{ store.currentSenador.data_nascimento ? formatDate(store.currentSenador.data_nascimento) : 'Indisponível' }}</span>
                    </div>

                    <div class="flex flex-col gap-1">
                      <div class="flex items-center gap-2 text-muted-foreground">
                        <GraduationCap class="h-4 w-4 text-primary-500" />
                        <span class="text-xs font-bold uppercase tracking-wider">Escolaridade</span>
                      </div>
                      <span class="pl-6">{{ store.currentSenador.escolaridade || 'Indisponível' }}</span>
                    </div>
                    <!-- CPF removed per user request -->
                  </div>
                </div>
              </BaseCard>

              <!-- Stats cards -->
              <div class="flex-1 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <BaseCard class="border-primary-100">
                  <div class="flex items-center justify-between">
                    <p class="text-sm text-muted-foreground">Gastos Totais Mandato</p>
                  </div>
                  <p v-if="totalGastos > 0" class="mt-2 text-3xl font-bold text-foreground">R$ {{ (totalGastos / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 }) }} mil</p>
                  <p v-else class="mt-2 text-xl font-bold text-muted-foreground">0</p>
                  <p class="mt-1 text-xs text-muted-foreground">Soma de todas despesas registradas</p>
                </BaseCard>

                <BaseCard class="border-primary-100">
                  <div class="flex items-center justify-between">
                    <p class="text-sm text-muted-foreground">Emendas</p>
                    <BaseBadge variant="secondary" class="bg-primary-100 text-primary-800">Mandato</BaseBadge>
                  </div>
                  <p v-if="store.totalEmendas > 0" class="mt-2 text-3xl font-bold text-foreground">R$ {{ (store.totalEmendas / 1000000).toFixed(1) }}M</p>
                  <p v-else class="mt-2 text-xl font-bold text-muted-foreground">Dados Indisponíveis</p>
                  <p class="mt-1 text-xs text-muted-foreground text-primary-600/70">Soma das emendas pagas ao senador</p>
                </BaseCard>

                <BaseCard class="sm:col-span-2 lg:col-span-3 border-primary-100">
                  <h3 class="font-semibold text-foreground mb-4">Principais Gastos por Categoria</h3>
                  <div class="space-y-3">
                    <div v-if="gastosCategorias.length === 0" class="py-6 text-center text-muted-foreground italic">
                      Dados Indisponíveis ou Sem Gastos
                    </div>
                    <div v-for="item in gastosCategorias" :key="item.categoria">
                      <div class="flex items-center justify-between text-sm mb-1">
                        <span class="text-muted-foreground">{{ item.categoria }}</span>
                        <span class="font-medium text-foreground">R$ {{ (item.valor / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 }) }} mil</span>
                      </div>
                      <div class="progress-bar bg-primary-100">
                        <div
                          class="progress-fill bg-primary-500"
                          :style="{ width: `${item.percentage}%` }"
                        />
                      </div>
                    </div>
                  </div>
                </BaseCard>
              </div>
            </div>
          </div>
        </section>
        
        <!-- Emendas Table Section -->
        <section class="py-8 bg-primary-50/30">
            <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <h3 class="text-xl font-bold text-foreground mb-4">Emendas Parlamentares</h3>
                <BaseCard variant="elevated" class="p-0 overflow-hidden border-primary-100 shadow-primary-900/5">
                    <div class="overflow-x-auto max-h-[600px] relative">
                        <table class="table-professional w-full border-collapse">
                            <thead class="sticky top-0 z-10 bg-card border-b border-primary-100 shadow-sm">
                                <tr>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b border-primary-100">Ano/Tipo</th>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b border-primary-100">Função</th>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b border-primary-100">Localidade</th>
                                    <th class="bg-card py-4 px-4 text-right font-bold text-xs uppercase tracking-wider text-muted-foreground border-b border-primary-100">Valor Pago</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-primary-50 bg-card">
                                <tr v-for="(emenda, index) in store.currentEmendas" :key="index" class="transition-colors">
                                    <td class="whitespace-nowrap px-4 py-3">
                                        <div class="flex flex-col">
                                            <span class="font-medium text-primary-900">{{ emenda.ano }}</span>
                                            <span class="text-xs text-muted-foreground">{{ emenda.tipo }}</span>
                                        </div>
                                    </td>
                                    <td class="text-muted-foreground px-4 py-3">{{ emenda.funcao }}</td>
                                    <td class="text-muted-foreground px-4 py-3">{{ emenda.localidade }}</td>
                                    <td class="text-right whitespace-nowrap font-medium text-primary-600 px-4 py-3">R$ {{ emenda.valorPago.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) }}</td>
                                </tr>
                                <tr v-if="store.currentEmendas.length === 0">
                                    <td colspan="4" class="py-12 text-center text-muted-foreground italic">Dados Indisponíveis</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </BaseCard>

                <!-- Pagination Emendas -->
                <div v-if="store.emendasTotalPages > 1" class="mt-4 flex items-center justify-between">
                    <p class="text-sm text-muted-foreground">
                        Página {{ store.emendasPage }} de {{ store.emendasTotalPages }}
                    </p>
                    <div class="flex gap-2">
                        <BaseButton 
                            variant="outline" 
                            size="sm" 
                            :disabled="store.emendasPage <= 1"
                            @click="store.fetchEmendasSenador(store.currentSenador!.id, store.emendasPage - 1)"
                        >
                            <ChevronLeft class="h-4 w-4 mr-1" /> Anterior
                        </BaseButton>
                        <BaseButton 
                            variant="outline" 
                            size="sm" 
                            :disabled="store.emendasPage >= store.emendasTotalPages"
                            @click="store.fetchEmendasSenador(store.currentSenador!.id, store.emendasPage + 1)"
                        >
                            Próxima <ChevronRight class="h-4 w-4 ml-1" />
                        </BaseButton>
                    </div>
                </div>
            </div>
        </section>

        <!-- Expenses Table Section -->
        <section class="py-8">
            <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <h3 class="text-xl font-bold text-foreground mb-4">Histórico de Despesas</h3>
                <BaseCard variant="elevated" class="p-0 overflow-hidden">
                    <div class="overflow-x-auto max-h-[600px] relative">
                        <table class="table-professional w-full border-collapse">
                            <thead class="sticky top-0 z-10 bg-card border-b shadow-sm">
                                <tr>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b">Data</th>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b">Descrição / Categoria</th>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b hidden sm:table-cell">Fornecedor</th>
                                    <th class="bg-card py-4 px-4 text-right font-bold text-xs uppercase tracking-wider text-muted-foreground border-b">Valor</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-border bg-card">
                                <tr v-for="(despesa, index) in store.currentDespesas" :key="index" class="transition-colors">
                                    <td class="whitespace-nowrap px-4 py-3">{{ despesa.mes }}/{{ despesa.ano }}</td>
                                    <td class="truncate max-w-xs px-4 py-3">{{ despesa.tipoDespesa || despesa.tipo_despesa }}</td>
                                    <td class="truncate max-w-xs hidden sm:table-cell px-4 py-3">{{ despesa.fornecedor || '--' }}</td>
                                    <td class="text-right whitespace-nowrap font-medium px-4 py-3">R$ {{ (despesa.valorReembolsado || despesa.valor || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 }) }}</td>
                                </tr>
                                <tr v-if="store.currentDespesas.length === 0">
                                    <td colspan="4" class="py-12 text-center text-muted-foreground italic">Dados Indisponíveis</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </BaseCard>

                <!-- Pagination Despesas -->
                <div v-if="store.despesasTotalPages > 1" class="mt-4 flex items-center justify-between">
                    <p class="text-sm text-muted-foreground">
                        Página {{ store.despesasPage }} de {{ store.despesasTotalPages }}
                    </p>
                    <div class="flex gap-2">
                        <BaseButton 
                            variant="outline" 
                            size="sm" 
                            :disabled="store.despesasPage <= 1"
                            @click="store.fetchDespesasSenador(store.currentSenador!.id, store.despesasPage - 1)"
                        >
                            <ChevronLeft class="h-4 w-4 mr-1" /> Anterior
                        </BaseButton>
                        <BaseButton 
                            variant="outline" 
                            size="sm" 
                            :disabled="store.despesasPage >= store.despesasTotalPages"
                            @click="store.fetchDespesasSenador(store.currentSenador!.id, store.despesasPage + 1)"
                        >
                            Próxima <ChevronRight class="h-4 w-4 ml-1" />
                        </BaseButton>
                    </div>
                </div>
            </div>
        </section>

      </template>

      <div v-else class="flex-1 flex items-center justify-center">
        <p class="text-muted-foreground">Senador não encontrado.</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronLeft, ChevronRight, Mail, Calendar, GraduationCap } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { useSenadoStore } from '@/stores/senado'

const route = useRoute()
const store = useSenadoStore()

const loadData = () => {
    const id = Number(route.params.id)
    if (id) {
        store.fetchSenador(id)
    }
}

onMounted(() => {
    loadData()
})

watch(() => route.params.id, () => {
    loadData()
})

watch(() => store.legislatura, () => {
    loadData()
})

const formatDate = (dateString: string) => {
    if (!dateString) return '--'
    const date = new Date(dateString)
    return date.toLocaleDateString('pt-BR')
}

const formatLegislatura = (legis: number) => {
  if (legis === 0) return 'Todas as legislaturas (Histórico)'
  const startYear = 2023 - (57 - legis) * 4
  const endYear = startYear + 3
  return `${legis}ª Legislatura (${startYear}-${endYear})`
}

watch(() => store.currentSenador, (newVal) => {
    if (newVal) {
        document.title = `${newVal.nome_civil} - Senado | Fiscaliza Brasil`
    }
}, { immediate: true })

const totalGastos = computed(() => {
    return store.totalDespesas
})

const gastosCategorias = computed(() => {
    const total = totalGastos.value
    if (total === 0 || store.currentCategorias.length === 0) return []

    return store.currentCategorias
        .map(c => ({
            categoria: c.categoria,
            valor: c.valor,
            percentage: (c.valor / total) * 100
        }))
        .slice(0, 5) // Top 5
})

</script>
