<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Breadcrumb -->
      <div class="bg-muted/30 border-b border-border">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <router-link :to="voltarLink" class="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
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
              <template v-if="currentParlamentar?.legislaturas_ativas?.length">
                <option :value="0">Todas as legislaturas (Histórico)</option>
                <option v-for="legis in currentParlamentar.legislaturas_ativas" :key="legis" :value="legis">
                  {{ formatLegislatura(legis) }}
                </option>
              </template>
              <template v-else-if="tipo === 'camara' && store.legislaturasDisponiveis?.length">
                <option :value="0">Todas as legislaturas (Histórico)</option>
                <option v-for="legis in store.legislaturasDisponiveis" :key="legis" :value="legis">
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

      <DetalheSkeleton v-if="store.loadingDetail" />

      <div v-else-if="store.error" class="flex-1 flex items-center justify-center min-h-[400px]">
        <p class="text-destructive">{{ store.error }}</p>
      </div>

      <template v-else-if="currentParlamentar">
        <!-- Scraping Banner -->
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-6">
          <ScrapingBanner
            :tipo="tipo"
            :em-andamento="store.scrapingStatus?.em_andamento ?? false"
            :camara-pendentes="store.scrapingStatus?.camara_pendentes ?? null"
            :senado-pendentes="store.scrapingStatus?.senado_pendentes ?? null"
          />
        </div>

        <!-- Profile -->
        <section class="py-8 bg-background border-b border-border/50">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div class="flex flex-col lg:flex-row gap-8">
              <!-- Profile card -->
              <BaseCard :class="profileCardClass">
                <div class="text-center">
                  <div class="h-32 w-32 mx-auto rounded-full border-4 border-primary/20 overflow-hidden bg-primary/10 flex items-center justify-center">
                    <img
                      :src="currentParlamentar.foto || '/placeholder-user.svg'"
                      :alt="nomeExibicao"
                      class="w-full h-full object-cover"
                      @error="($event.target as HTMLImageElement).src = '/placeholder-user.svg'"
                    />
                  </div>

                  <h1 class="mt-4 text-xl font-bold text-foreground">{{ nomeExibicao }}</h1>

                  <div class="mt-2 flex flex-wrap items-center justify-center gap-2">
                    <BaseBadge variant="outline">Partido: {{ currentParlamentar.sigla_partido }}</BaseBadge>
                    <BaseBadge v-if="siglaUf" variant="outline">Estado: {{ siglaUf }}</BaseBadge>
                  </div>

                  <div class="mt-6 space-y-3 text-sm text-left">
                    <div class="flex flex-col gap-1">
                      <div class="flex items-center gap-2 text-muted-foreground">
                        <User class="h-4 w-4 text-primary" />
                        <span class="text-xs font-bold uppercase tracking-wider">Nome Civil</span>
                      </div>
                      <span class="pl-6">{{ currentParlamentar.nome_civil }}</span>
                    </div>

                    <div class="flex flex-col gap-1">
                      <div class="flex items-center gap-2 text-muted-foreground">
                        <Mail class="h-4 w-4 text-primary" />
                        <span class="text-xs font-bold uppercase tracking-wider">E-mail</span>
                      </div>
                      <span class="truncate pl-6">{{ currentParlamentar.email || 'Indisponível' }}</span>
                    </div>

                    <div class="flex flex-col gap-1">
                      <div class="flex items-center gap-2 text-muted-foreground">
                        <Calendar class="h-4 w-4 text-primary" />
                        <span class="text-xs font-bold uppercase tracking-wider">Nascimento</span>
                      </div>
                      <span class="pl-6">{{ currentParlamentar.data_nascimento ? formatDate(currentParlamentar.data_nascimento) : 'Indisponível' }}</span>
                    </div>

                    <div class="flex flex-col gap-1">
                      <div class="flex items-center gap-2 text-muted-foreground">
                        <GraduationCap class="h-4 w-4 text-primary" />
                        <span class="text-xs font-bold uppercase tracking-wider">Escolaridade</span>
                      </div>
                      <span class="pl-6">{{ currentParlamentar.escolaridade || 'Indisponível' }}</span>
                    </div>
                    <!-- CPF removed per user request -->
                  </div>
                </div>
              </BaseCard>

              <!-- Stats cards -->
              <div class="flex-1 grid gap-4 sm:grid-cols-2">
                <BaseCard :class="statsCardClass">
                  <div class="flex items-center justify-between">
                    <p class="text-sm text-muted-foreground">Gastos Totais Mandato</p>
                  </div>
                  <p v-if="totalGastos > 0" class="mt-2 text-3xl font-bold text-foreground">{{ formatCurrency(totalGastos) }}</p>
                  <p v-else class="mt-2 text-xl font-bold text-muted-foreground">{{ tipo === 'senado' ? '0' : 'Dados Indisponíveis' }}</p>
                  <p class="mt-1 text-xs text-muted-foreground">Soma de todas despesas registradas</p>
                </BaseCard>

                <BaseCard :class="statsCardClass">
                  <div class="flex items-center justify-between">
                    <p class="text-sm text-muted-foreground">Emendas</p>
                    <BaseBadge variant="secondary" :class="emendasBadgeClass">Mandato</BaseBadge>
                  </div>
                  <p v-if="store.totalEmendas > 0" class="mt-2 text-3xl font-bold text-foreground">{{ formatCurrency(store.totalEmendas) }}</p>
                  <p v-else class="mt-2 text-xl font-bold text-muted-foreground">Dados Indisponíveis</p>
                  <p class="mt-1 text-xs text-muted-foreground">Soma das emendas pagas ao {{ tipo === 'camara' ? 'deputado' : 'senador' }}</p>
                </BaseCard>

                <BaseCard :class="['sm:col-span-2', categoriasCardClass]">
                  <h3 class="font-semibold text-foreground mb-4">Principais Gastos por Categoria</h3>
                  <div class="space-y-3">
                    <div v-if="gastosCategorias.length === 0" class="py-6 text-center text-muted-foreground italic">
                      {{ tipo === 'senado' ? 'Dados Indisponíveis ou Sem Gastos' : 'Dados Indisponíveis' }}
                    </div>
                    <div v-for="item in gastosCategorias" :key="item.categoria">
                      <div class="flex items-start justify-between text-sm mb-1 gap-2">
                        <span class="text-muted-foreground">{{ item.categoria }}</span>
                        <span class="font-medium text-foreground whitespace-nowrap shrink-0 text-right">{{ formatCurrency(item.valor) }}</span>
                      </div>
                      <div class="progress-bar" :class="progressBarClass">
                        <div
                          class="progress-fill"
                          :class="progressFillClass"
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
        <section class="py-8" :class="emendasSectionClass">
            <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <h3 class="text-xl font-bold text-foreground mb-4">Emendas Parlamentares</h3>
                <BaseCard variant="elevated" class="p-0 overflow-hidden" :class="emendasCardClass">
                    <div :class="['overflow-x-auto max-h-[600px] relative', { 'min-h-[300px]': store.loadingEmendas }]">
                        <table class="table-professional w-full border-collapse">
                            <thead class="sticky top-0 z-10 bg-card border-b shadow-sm" :class="emendasTheadClass">
                                <tr>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b" :class="emendasThBorderClass">Ano/Tipo</th>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b" :class="emendasThBorderClass">Função</th>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b" :class="emendasThBorderClass">Localidade</th>
                                    <th class="bg-card py-4 px-4 text-right font-bold text-xs uppercase tracking-wider text-muted-foreground border-b" :class="emendasThBorderClass">Valor Pago</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-border bg-card" :class="emendasTbodyClass">
                                <tr v-if="store.loadingEmendas">
                                    <td colspan="4" class="py-12 text-center text-muted-foreground">
                                        <span class="inline-block animate-spin h-5 w-5 border-2 border-primary border-t-transparent rounded-full mr-2 align-middle"></span>
                                        Carregando...
                                    </td>
                                </tr>
                                <tr v-for="(emenda, index) in store.currentEmendas" :key="index" class="hover:bg-muted/50 transition-colors" v-else>
                                    <td class="whitespace-nowrap px-4 py-3">
                                        <div class="flex flex-col">
                                            <span class="font-medium" :class="emendasAnoClass">{{ emenda.ano }}</span>
                                            <span class="text-xs text-muted-foreground">{{ emenda.tipo }}</span>
                                        </div>
                                    </td>
                                    <td class="px-4 py-3" :class="emendasCellClass">{{ emenda.funcao }}</td>
                                    <td class="px-4 py-3" :class="emendasCellClass">{{ emenda.localidade }}</td>
                                    <td class="text-right whitespace-nowrap font-medium px-4 py-3" :class="emendasValorClass">R$ {{ emenda.valorPago.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) }}</td>
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
                            @click="fetchEmendas(store.emendasPage - 1)"
                        >
                            <ChevronLeft class="h-4 w-4 mr-1" /> Anterior
                        </BaseButton>
                        <BaseButton
                            variant="outline"
                            size="sm"
                            :disabled="store.emendasPage >= store.emendasTotalPages"
                            @click="fetchEmendas(store.emendasPage + 1)"
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
                    <div :class="['overflow-x-auto max-h-[600px] relative', { 'min-h-[300px]': store.loadingDespesas }]">
                        <table class="table-professional w-full border-collapse">
                            <thead class="sticky top-0 z-10 bg-card border-b shadow-sm">
                                <tr>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b">Data</th>
                                    <th class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b">{{ tipo === 'senado' ? 'Descrição / Categoria' : 'Descrição' }}</th>
                                    <th v-if="tipo === 'senado'" class="bg-card py-4 px-4 text-left font-bold text-xs uppercase tracking-wider text-muted-foreground border-b hidden sm:table-cell">Fornecedor</th>
                                    <th class="bg-card py-4 px-4 text-right font-bold text-xs uppercase tracking-wider text-muted-foreground border-b">Valor</th>
                                    <th v-if="tipo === 'camara'" class="bg-card py-4 px-4 text-center font-bold text-xs uppercase tracking-wider text-muted-foreground border-b hidden sm:table-cell">Doc</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-border bg-card">
                                <tr v-if="store.loadingDespesas">
                                    <td :colspan="despesasColspan" class="py-12 text-center text-muted-foreground">
                                        <span class="inline-block animate-spin h-5 w-5 border-2 border-primary border-t-transparent rounded-full mr-2 align-middle"></span>
                                        Carregando...
                                    </td>
                                </tr>
                                <tr v-for="(despesa, index) in store.currentDespesas" :key="index" class="hover:bg-muted/50 transition-colors" v-else>
                                    <td class="whitespace-nowrap px-4 py-3">{{ despesa.mes }}/{{ despesa.ano }}</td>
                                    <td class="truncate max-w-xs px-4 py-3">{{ despesa.tipoDespesa || despesa.tipo_despesa }}</td>
                                    <td v-if="tipo === 'senado'" class="truncate max-w-xs hidden sm:table-cell px-4 py-3">{{ despesa.fornecedor || '--' }}</td>
                                    <td class="text-right whitespace-nowrap font-medium px-4 py-3">R$ {{ (despesa.valorReembolsado || despesa.valor || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 }) }}</td>
                                    <td v-if="tipo === 'camara'" class="text-center hidden sm:table-cell px-4 py-3">
                                        <a v-if="despesa.url_documento" :href="despesa.url_documento" target="_blank" class="text-primary hover:text-primary-700 transition-colors" title="Ver documento">
                                            <FileText class="h-4 w-4 mx-auto" />
                                        </a>
                                        <span v-else class="text-muted-foreground">--</span>
                                    </td>
                                </tr>
                                <tr v-if="store.currentDespesas.length === 0">
                                    <td :colspan="despesasColspan" class="py-12 text-center text-muted-foreground italic">Dados Indisponíveis</td>
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
                            @click="fetchDespesas(store.despesasPage - 1)"
                        >
                            <ChevronLeft class="h-4 w-4 mr-1" /> Anterior
                        </BaseButton>
                        <BaseButton
                            variant="outline"
                            size="sm"
                            :disabled="store.despesasPage >= store.despesasTotalPages"
                            @click="fetchDespesas(store.despesasPage + 1)"
                        >
                            Próxima <ChevronRight class="h-4 w-4 ml-1" />
                        </BaseButton>
                    </div>
                </div>
            </div>
        </section>

      </template>

      <div v-else class="flex-1 flex items-center justify-center">
        <p class="text-muted-foreground">{{ tipo === 'camara' ? 'Deputado' : 'Senador' }} não encontrado.</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronLeft, ChevronRight, Mail, Calendar, GraduationCap, FileText, User } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ScrapingBanner from '@/components/ScrapingBanner.vue'
import DetalheSkeleton from '@/components/camara/DetalheSkeleton.vue'
import { useCamaraStore } from "@/stores/camara"
import { useSenadoStore } from '@/stores/senado'
import { formatCurrency } from "@/utils/format"

const props = defineProps<{
  tipo: 'camara' | 'senado'
}>()

const route = useRoute()
const camaraStore = useCamaraStore()
const senadoStore = useSenadoStore()

const store = computed(() => props.tipo === 'camara' ? camaraStore : senadoStore)

const currentParlamentar = computed(() => {
  return props.tipo === 'camara' ? camaraStore.currentDeputado : senadoStore.currentSenador
})

const nomeExibicao = computed(() => {
  const p = currentParlamentar.value as any
  if (!p) return ''
  return p.nome_eleitoral || p.nome_parlamentar || p.nome_civil || ''
})

const siglaUf = computed(() => {
  const p = currentParlamentar.value
  if (!p) return ''
  return props.tipo === 'camara' ? (p as any).sigla_uf : (p as any).uf
})

const voltarLink = computed(() => {
  return props.tipo === 'camara' ? '/camara/deputados' : '/senado/senadores'
})

const despesasColspan = computed(() => props.tipo === 'camara' ? 4 : 4)

// Classes condicionais para manter consistência visual com os estilos originais
const profileCardClass = computed(() => props.tipo === 'senado' ? 'border-primary-100' : '')
const statsCardClass = computed(() => props.tipo === 'senado' ? 'border-primary-100' : '')
const emendasBadgeClass = computed(() => props.tipo === 'senado' ? 'bg-primary-100 text-primary-800' : '')
const categoriasCardClass = computed(() => props.tipo === 'senado' ? 'border-primary-100' : '')
const progressBarClass = computed(() => props.tipo === 'senado' ? 'bg-primary-100' : '')
const progressFillClass = computed(() => props.tipo === 'senado' ? 'bg-primary-500' : '')
const emendasSectionClass = computed(() => props.tipo === 'senado' ? 'bg-primary-50/30' : 'bg-muted/20')
const emendasCardClass = computed(() => props.tipo === 'senado' ? 'border-primary-100 shadow-primary-900/5' : '')
const emendasTheadClass = computed(() => props.tipo === 'senado' ? 'border-primary-100' : '')
const emendasThBorderClass = computed(() => props.tipo === 'senado' ? 'border-primary-100' : '')
const emendasTbodyClass = computed(() => props.tipo === 'senado' ? 'divide-primary-50' : '')
const emendasAnoClass = computed(() => props.tipo === 'senado' ? 'text-primary-900' : '')
const emendasCellClass = computed(() => props.tipo === 'senado' ? 'text-muted-foreground' : '')
const emendasValorClass = computed(() => props.tipo === 'senado' ? 'text-primary-600' : 'text-primary')

const loadData = async () => {
    const id = Number(route.params.id)
    if (id) {
        if (props.tipo === 'camara') {
            await camaraStore.fetchDeputado(id)
            await camaraStore.fetchScrapingStatus()
            camaraStore.iniciarPollingDeputado(id)
        } else {
            await senadoStore.fetchSenador(id)
            await senadoStore.fetchScrapingStatus()
            senadoStore.iniciarPollingSenador(id)
        }
    }
}

onMounted(() => {
    loadData()
})

onUnmounted(() => {
    store.value.pararPolling()
})

watch(() => route.params.id, () => {
    store.value.pararPolling()
    loadData()
})

watch(() => store.value.legislatura, () => {
    store.value.pararPolling()
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
    return store.value.totalDespesas
})

const gastosCategorias = computed(() => {
    const total = totalGastos.value
    if (total === 0 || !store.value.currentCategorias || store.value.currentCategorias.length === 0) return []

    return store.value.currentCategorias
        .map(c => ({
            categoria: c.categoria,
            valor: c.valor,
            percentage: (c.valor / total) * 100
        }))
        .slice(0, 5) // Top 5
})

const fetchEmendas = (page: number) => {
    const id = Number(route.params.id)
    if (props.tipo === 'camara') {
        camaraStore.fetchEmendasDeputado(id, page)
    } else {
        senadoStore.fetchEmendasSenador(id, page)
    }
}

const fetchDespesas = (page: number) => {
    const id = Number(route.params.id)
    if (props.tipo === 'camara') {
        camaraStore.fetchDespesasDeputado(id, page)
    } else {
        senadoStore.fetchDespesasSenador(id, page)
    }
}

watch(() => currentParlamentar.value, (newVal) => {
    if (newVal) {
        const casa = props.tipo === 'camara' ? 'Câmara' : 'Senado'
        document.title = `${newVal.nome_civil} - ${casa} | Fiscaliza Brasil`
    }
}, { immediate: true })

</script>
