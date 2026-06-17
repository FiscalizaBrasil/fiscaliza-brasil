<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Breadcrumb -->
      <div class="bg-muted/30 border-b border-border">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <router-link to="/camara/deputados" class="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
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
              <template v-if="store.currentDeputado?.legislaturas_ativas?.length">
                <option :value="0">Todas as legislaturas (Histórico)</option>
                <option v-for="legis in store.currentDeputado.legislaturas_ativas" :key="legis" :value="legis">
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

      <BaseLoading v-if="store.loadingDetail" message="Carregando detalhes do deputado..." full-page />

      <div v-else-if="store.error" class="flex-1 flex items-center justify-center min-h-[400px]">
        <p class="text-destructive">{{ store.error }}</p>
      </div>

      <template v-else-if="store.currentDeputado">
        <!-- Profile -->
        <section class="py-8 bg-background border-b border-border/50">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div class="flex flex-col lg:flex-row gap-8">
              <!-- Profile card -->
              <BaseCard class="lg:w-80 flex-shrink-0">
                <div class="text-center">
                  <div class="h-32 w-32 mx-auto rounded-full border-4 border-primary/20 overflow-hidden bg-primary/10 flex items-center justify-center">
                    <img
                      :src="store.currentDeputado.foto || '/placeholder-user.svg'"
                      :alt="store.currentDeputado.nome_civil"
                      class="w-full h-full object-cover"
                      @error="($event.target as HTMLImageElement).src = '/placeholder-user.svg'"
                    />
                  </div>

                  <h1 class="mt-4 text-xl font-bold text-foreground">{{ store.currentDeputado.nome_civil }}</h1>

                  <div class="mt-2 flex flex-wrap items-center justify-center gap-2">
                    <BaseBadge variant="outline">Partido: {{ store.currentDeputado.sigla_partido }}</BaseBadge>
                    <BaseBadge v-if="store.currentDeputado.sigla_uf" variant="outline">Estado: {{ store.currentDeputado.sigla_uf }}</BaseBadge>
                  </div>

                  <div class="mt-6 space-y-3 text-sm text-left">
                    <div class="flex flex-col gap-1">
                      <div class="flex items-center gap-2 text-muted-foreground">
                        <Mail class="h-4 w-4 text-primary" />
                        <span class="text-xs font-bold uppercase tracking-wider">E-mail</span>
                      </div>
                      <span class="truncate pl-6">{{ store.currentDeputado.email || 'Indisponível' }}</span>
                    </div>

                    <div class="flex flex-col gap-1">
                      <div class="flex items-center gap-2 text-muted-foreground">
                        <Calendar class="h-4 w-4 text-primary" />
                        <span class="text-xs font-bold uppercase tracking-wider">Nascimento</span>
                      </div>
                      <span class="pl-6">{{ store.currentDeputado.data_nascimento ? formatDate(store.currentDeputado.data_nascimento) : 'Indisponível' }}</span>
                    </div>

                    <div class="flex flex-col gap-1">
                      <div class="flex items-center gap-2 text-muted-foreground">
                        <GraduationCap class="h-4 w-4 text-primary" />
                        <span class="text-xs font-bold uppercase tracking-wider">Escolaridade</span>
                      </div>
                      <span class="pl-6">{{ store.currentDeputado.escolaridade || 'Indisponível' }}</span>
                    </div>
                    <!-- CPF removed per user request -->
                  </div>
                </div>
              </BaseCard>

              <!-- Stats cards -->
              <div class="flex-1 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <BaseCard>
                  <div class="flex items-center justify-between">
                    <p class="text-sm text-muted-foreground">Gastos Totais Mandato</p>
                  </div>
                  <p v-if="totalGastos > 0" class="mt-2 text-3xl font-bold text-foreground">R$ {{ (totalGastos / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 }) }} mil</p>
                  <p v-else class="mt-2 text-xl font-bold text-muted-foreground">Dados Indisponíveis</p>
                  <p class="mt-1 text-xs text-muted-foreground">Soma de todas despesas registradas</p>
                </BaseCard>

                 <!-- Placeholder for stats not currently in API -->
                <BaseCard>
                  <div class="flex items-center justify-between">
                    <p class="text-sm text-muted-foreground">Emendas</p>
                    <BaseBadge variant="secondary">Mandato</BaseBadge>
                  </div>
                  <p v-if="store.totalEmendas > 0" class="mt-2 text-3xl font-bold text-foreground">R$ {{ (store.totalEmendas / 1000000).toFixed(1) }}M</p>
                  <p v-else class="mt-2 text-xl font-bold text-muted-foreground">Dados Indisponíveis</p>
                  <p class="mt-1 text-xs text-muted-foreground">Soma das emendas pagas ao deputado</p>
                </BaseCard>

                <BaseCard class="sm:col-span-2 lg:col-span-3">
                  <h3 class="font-semibold text-foreground mb-4">Principais Gastos por Categoria</h3>
                  <div class="space-y-3">
                    <div v-if="gastosCategorias.length === 0" class="py-6 text-center text-muted-foreground italic">
                      Dados Indisponíveis
                    </div>
                    <div v-for="item in gastosCategorias" :key="item.categoria">
                      <div class="flex items-center justify-between text-sm mb-1">
                        <span class="text-muted-foreground">{{ item.categoria }}</span>
                        <span class="font-medium text-foreground">R$ {{ (item.valor / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 }) }} mil</span>
                      </div>
                      <div class="progress-bar">
                        <div
                          class="progress-fill"
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
        <section class="py-8 bg-muted/20">
            <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <h3 class="text-xl font-bold text-foreground mb-4">Emendas Parlamentares</h3>
                <BaseCard variant="elevated" class="p-0 overflow-hidden">
                    <div class="overflow-x-auto max-h-[600px] relative">
                        <table class="table-professional w-full border-collapse">
                            <thead class="sticky top-0 z-10 bg-card border-b shadow-sm">
                                <tr>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b">Ano/Tipo</th>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b">Função</th>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b">Localidade</th>
                                    <th class="bg-card py-4 px-4 text-right font-bold text-xs uppercase tracking-wider text-muted-foreground border-b">Valor Pago</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-border bg-card">
                                <tr v-for="(emenda, index) in store.currentEmendas" :key="index" class="hover:bg-muted/50 transition-colors">
                                    <td class="whitespace-nowrap px-4 py-3">
                                        <div class="flex flex-col">
                                            <span class="font-medium">{{ emenda.ano }}</span>
                                            <span class="text-xs text-muted-foreground">{{ emenda.tipo }}</span>
                                        </div>
                                    </td>
                                    <td class="px-4 py-3">{{ emenda.funcao }}</td>
                                    <td class="px-4 py-3">{{ emenda.localidade }}</td>
                                    <td class="text-right whitespace-nowrap font-medium text-primary px-4 py-3">R$ {{ emenda.valorPago.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) }}</td>
                                </tr>
                                <tr v-if="store.currentEmendas.length === 0">
                                    <td colspan="4" class="py-12 text-center text-muted-foreground italic">Dados Indisponíveis</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </BaseCard>

                <div v-if="store.emendasTotalPages > 1" class="mt-4 flex items-center justify-between">
                    <p class="text-sm text-muted-foreground">
                        Página {{ store.emendasPage }} de {{ store.emendasTotalPages }}
                    </p>
                    <div class="flex gap-2">
                        <BaseButton
                            variant="outline"
                            size="sm"
                            :disabled="store.emendasPage <= 1"
                            @click="store.fetchEmendasDeputado(store.currentDeputado!.id, store.emendasPage - 1)"
                        >
                            <ChevronLeft class="h-4 w-4 mr-1" /> Anterior
                        </BaseButton>
                        <BaseButton
                            variant="outline"
                            size="sm"
                            :disabled="store.emendasPage >= store.emendasTotalPages"
                            @click="store.fetchEmendasDeputado(store.currentDeputado!.id, store.emendasPage + 1)"
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
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b">Descrição</th>
                                    <th class="bg-card py-4 px-4 text-right font-bold text-xs uppercase tracking-wider text-muted-foreground border-b">Valor</th>
                                    <th class="bg-card py-4 px-4 text-center font-bold text-xs uppercase tracking-wider text-muted-foreground border-b hidden sm:table-cell">Doc</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-border bg-card">
                                <tr v-for="(despesa, index) in store.currentDespesas" :key="index" class="hover:bg-muted/50 transition-colors">
                                    <td class="whitespace-nowrap px-4 py-3">{{ despesa.mes }}/{{ despesa.ano }}</td>
                                    <td class="truncate max-w-xs px-4 py-3">{{ despesa.tipo_despesa }}</td>
                                    <td class="text-right whitespace-nowrap font-medium px-4 py-3">R$ {{ despesa.valor.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) }}</td>
                                    <td class="text-center hidden sm:table-cell px-4 py-3">
                                        <a v-if="despesa.url_documento" :href="despesa.url_documento" target="_blank" class="text-primary hover:text-primary-700 transition-colors" title="Ver documento">
                                            <FileText class="h-4 w-4 mx-auto" />
                                        </a>
                                        <span v-else class="text-muted-foreground">--</span>
                                    </td>
                                </tr>
                                <tr v-if="store.currentDespesas.length === 0">
                                    <td colspan="4" class="py-12 text-center text-muted-foreground italic">Dados Indisponíveis</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </BaseCard>

                <div v-if="store.despesasTotalPages > 1" class="mt-4 flex items-center justify-between">
                    <p class="text-sm text-muted-foreground">
                        Página {{ store.despesasPage }} de {{ store.despesasTotalPages }}
                    </p>
                    <div class="flex gap-2">
                        <BaseButton
                            variant="outline"
                            size="sm"
                            :disabled="store.despesasPage <= 1"
                            @click="store.fetchDespesasDeputado(store.currentDeputado!.id, store.despesasPage - 1)"
                        >
                            <ChevronLeft class="h-4 w-4 mr-1" /> Anterior
                        </BaseButton>
                        <BaseButton
                            variant="outline"
                            size="sm"
                            :disabled="store.despesasPage >= store.despesasTotalPages"
                            @click="store.fetchDespesasDeputado(store.currentDeputado!.id, store.despesasPage + 1)"
                        >
                            Próxima <ChevronRight class="h-4 w-4 ml-1" />
                        </BaseButton>
                    </div>
                </div>
            </div>
        </section>

      </template>

      <div v-else class="flex-1 flex items-center justify-center">
        <p class="text-muted-foreground">Deputado não encontrado.</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronLeft, ChevronRight, Mail, Calendar, GraduationCap, FileText } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { useCamaraStore } from "@/stores/camara"

const route = useRoute()
const store = useCamaraStore()

const loadData = () => {
    const id = Number(route.params.id)
    if (id) {
        store.fetchDeputado(id)
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

const totalGastos = computed(() => {
    return store.totalDespesas
})

const gastosCategorias = computed(() => {
    const total = totalGastos.value
    if (total === 0 || !store.currentCategorias || store.currentCategorias.length === 0) return []

    return store.currentCategorias
        .map(c => ({
            categoria: c.categoria,
            valor: c.valor,
            percentage: (c.valor / total) * 100
        }))
        .slice(0, 5) // Top 5
})

watch(() => store.currentDeputado, (newVal) => {
    if (newVal) {
        document.title = `${newVal.nome_civil} - Câmara | Fiscaliza Brasil`
    }
}, { immediate: true })

</script>
