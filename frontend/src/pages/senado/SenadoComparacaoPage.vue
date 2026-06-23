<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Hero -->
      <section class="bg-background border-b border-border/50 py-12">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex items-center gap-3 mb-2">
            <Scale class="h-8 w-8 text-primary" />
            <h1 class="text-3xl font-bold text-foreground sm:text-4xl">Comparar Senadores</h1>
          </div>
          <p class="mt-2 text-muted-foreground max-w-2xl">
            Compare lado a lado os perfis, gastos e categorias de despesas de dois senadores.
          </p>
        </div>
      </section>

      <!-- Selection Section -->
      <section class="py-8 border-b border-border">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Selector A -->
            <div>
              <label class="block text-sm font-medium text-foreground mb-2">Senador A</label>
              <div class="relative">
                <div class="flex items-center gap-2">
                  <div class="relative flex-1">
                    <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <input
                      v-model="searchA"
                      type="text"
                      placeholder="Buscar senador por nome..."
                      class="input-base pl-10 pr-4 py-2.5 rounded-lg"
                      @focus="showDropdownA = true"
                      @blur="hideDropdown('A')"
                    />
                  </div>
                  <button
                    v-if="selectedA"
                    @click="clearSelection('A')"
                    class="p-2.5 rounded-lg border border-border hover:bg-muted transition-colors"
                    title="Limpar seleção"
                  >
                    <X class="h-4 w-4 text-muted-foreground" />
                  </button>
                </div>
                <!-- Dropdown A -->
                <div
                  v-if="showDropdownA && filteredListA.length > 0 && !selectedA"
                  class="absolute z-20 mt-1 w-full max-h-60 overflow-y-auto rounded-lg border border-border bg-background shadow-lg"
                >
                  <button
                    v-for="sen in filteredListA"
                    :key="sen.id"
                    class="flex items-center gap-3 w-full px-4 py-2.5 text-left hover:bg-muted transition-colors"
                    @mousedown.prevent="selectSenador('A', sen)"
                  >
                    <img
                      :src="sen.foto || '/placeholder-user.svg'"
                      :alt="sen.nome"
                      class="h-8 w-8 rounded-full object-cover border border-border"
                      @error="($event.target as HTMLImageElement).src = '/placeholder-user.svg'"
                    />
                    <div>
                      <p class="text-sm font-medium text-foreground">{{ sen.nome }}</p>
                      <p class="text-xs text-muted-foreground">{{ sen.partido }} - {{ sen.estado }}</p>
                    </div>
                  </button>
                </div>
              </div>
              <!-- Selected preview A -->
              <div v-if="selectedA" class="mt-3 flex items-center gap-3 p-3 rounded-lg bg-primary/5 border border-primary/20">
                <img
                  :src="selectedA.foto || '/placeholder-user.svg'"
                  :alt="selectedA.nome"
                  class="h-10 w-10 rounded-full object-cover border-2 border-primary/30"
                  @error="($event.target as HTMLImageElement).src = '/placeholder-user.svg'"
                />
                <div>
                  <p class="text-sm font-semibold text-foreground">{{ selectedA.nome }}</p>
                  <p class="text-xs text-muted-foreground">{{ selectedA.partido }} - {{ selectedA.estado }}</p>
                </div>
              </div>
            </div>

            <!-- Selector B -->
            <div>
              <label class="block text-sm font-medium text-foreground mb-2">Senador B</label>
              <div class="relative">
                <div class="flex items-center gap-2">
                  <div class="relative flex-1">
                    <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <input
                      v-model="searchB"
                      type="text"
                      placeholder="Buscar senador por nome..."
                      class="input-base pl-10 pr-4 py-2.5 rounded-lg"
                      @focus="showDropdownB = true"
                      @blur="hideDropdown('B')"
                    />
                  </div>
                  <button
                    v-if="selectedB"
                    @click="clearSelection('B')"
                    class="p-2.5 rounded-lg border border-border hover:bg-muted transition-colors"
                    title="Limpar seleção"
                  >
                    <X class="h-4 w-4 text-muted-foreground" />
                  </button>
                </div>
                <!-- Dropdown B -->
                <div
                  v-if="showDropdownB && filteredListB.length > 0 && !selectedB"
                  class="absolute z-20 mt-1 w-full max-h-60 overflow-y-auto rounded-lg border border-border bg-background shadow-lg"
                >
                  <button
                    v-for="sen in filteredListB"
                    :key="sen.id"
                    class="flex items-center gap-3 w-full px-4 py-2.5 text-left hover:bg-muted transition-colors"
                    @mousedown.prevent="selectSenador('B', sen)"
                  >
                    <img
                      :src="sen.foto || '/placeholder-user.svg'"
                      :alt="sen.nome"
                      class="h-8 w-8 rounded-full object-cover border border-border"
                      @error="($event.target as HTMLImageElement).src = '/placeholder-user.svg'"
                    />
                    <div>
                      <p class="text-sm font-medium text-foreground">{{ sen.nome }}</p>
                      <p class="text-xs text-muted-foreground">{{ sen.partido }} - {{ sen.estado }}</p>
                    </div>
                  </button>
                </div>
              </div>
              <!-- Selected preview B -->
              <div v-if="selectedB" class="mt-3 flex items-center gap-3 p-3 rounded-lg bg-accent/5 border border-accent/20">
                <img
                  :src="selectedB.foto || '/placeholder-user.svg'"
                  :alt="selectedB.nome"
                  class="h-10 w-10 rounded-full object-cover border-2 border-accent/30"
                  @error="($event.target as HTMLImageElement).src = '/placeholder-user.svg'"
                />
                <div>
                  <p class="text-sm font-semibold text-foreground">{{ selectedB.nome }}</p>
                  <p class="text-xs text-muted-foreground">{{ selectedB.partido }} - {{ selectedB.estado }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Compare button -->
          <div class="mt-6 flex justify-center">
            <BaseButton
              :disabled="!selectedA || !selectedB || loadingComparison"
              @click="compareSenadores"
            >
              <Scale class="h-4 w-4 mr-2" />
              {{ loadingComparison ? '...' : 'Comparar Senadores' }}
            </BaseButton>
          </div>
        </div>
      </section>

      <BaseLoading v-if="loadingComparison" message="Carregando dados para comparação..." />

      <!-- Comparison Results -->
      <template v-if="comparisonReady && senadorA && senadorB">
        <!-- Profile Comparison -->
        <section class="py-8">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <h2 class="text-xl font-bold text-foreground mb-6 flex items-center gap-2">
              <UserCheck class="h-5 w-5 text-primary" />
              Perfil
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Senador A Profile -->
              <BaseCard>
                <div class="text-center">
                  <div class="h-24 w-24 mx-auto rounded-full border-4 border-primary/20 overflow-hidden bg-primary/10">
                    <img
                      :src="senadorA.foto || '/placeholder-user.svg'"
                      :alt="senadorA.nome_civil"
                      class="w-full h-full object-cover"
                      @error="($event.target as HTMLImageElement).src = '/placeholder-user.svg'"
                    />
                  </div>
                  <h3 class="mt-3 text-lg font-bold text-foreground">{{ senadorA.nome_civil }}</h3>
                  <div class="mt-2 flex flex-wrap items-center justify-center gap-2">
                    <BaseBadge variant="outline">Partido: {{ senadorA.sigla_partido }}</BaseBadge>
                    <BaseBadge v-if="senadorA.uf" variant="outline">Estado: {{ senadorA.uf }}</BaseBadge>
                  </div>
                  <div class="mt-4 space-y-2 text-sm text-left">
                    <div class="flex items-center gap-3 text-muted-foreground" v-if="senadorA.email">
                      <Mail class="h-4 w-4 text-primary flex-shrink-0" />
                      <span class="truncate">{{ senadorA.email }}</span>
                    </div>
                    <div class="flex items-center gap-3 text-muted-foreground" v-if="senadorA.data_nascimento">
                      <Calendar class="h-4 w-4 text-primary flex-shrink-0" />
                      <span>{{ formatDate(senadorA.data_nascimento) }}</span>
                    </div>
                  </div>
                </div>
              </BaseCard>

              <!-- Senador B Profile -->
              <BaseCard>
                <div class="text-center">
                  <div class="h-24 w-24 mx-auto rounded-full border-4 border-accent/20 overflow-hidden bg-accent/10">
                    <img
                      :src="senadorB.foto || '/placeholder-user.svg'"
                      :alt="senadorB.nome_civil"
                      class="w-full h-full object-cover"
                      @error="($event.target as HTMLImageElement).src = '/placeholder-user.svg'"
                    />
                  </div>
                  <h3 class="mt-3 text-lg font-bold text-foreground">{{ senadorB.nome_civil }}</h3>
                  <div class="mt-2 flex flex-wrap items-center justify-center gap-2">
                    <BaseBadge variant="outline">Partido: {{ senadorB.sigla_partido }}</BaseBadge>
                    <BaseBadge v-if="senadorB.uf" variant="outline">Estado: {{ senadorB.uf }}</BaseBadge>
                  </div>
                  <div class="mt-4 space-y-2 text-sm text-left">
                    <div class="flex items-center gap-3 text-muted-foreground" v-if="senadorB.email">
                      <Mail class="h-4 w-4 text-accent flex-shrink-0" />
                      <span class="truncate">{{ senadorB.email }}</span>
                    </div>
                    <div class="flex items-center gap-3 text-muted-foreground" v-if="senadorB.data_nascimento">
                      <Calendar class="h-4 w-4 text-accent flex-shrink-0" />
                      <span>{{ formatDate(senadorB.data_nascimento) }}</span>
                    </div>
                  </div>
                </div>
              </BaseCard>
            </div>
          </div>
        </section>

        <!-- Expenses Comparison -->
        <section class="py-8 bg-muted/30">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <h2 class="text-xl font-bold text-foreground mb-6 flex items-center gap-2">
              <DollarSign class="h-5 w-5 text-primary" />
              Gastos Totais
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <BaseCard>
                <div class="text-center">
                  <p class="text-sm text-muted-foreground">{{ senadorA.nome_civil }}</p>
                  <p class="mt-1 text-3xl font-bold" :class="totalA <= totalB ? 'text-green-600' : 'text-red-500'">
                    R$ {{ formatCurrency(totalA) }}
                  </p>
                  <BaseBadge v-if="totalA === totalB" variant="secondary" class="mt-2">Empate</BaseBadge>
                  <BaseBadge v-else-if="totalA <= totalB" variant="success" class="mt-2">Menor gasto</BaseBadge>
                  <BaseBadge v-else variant="destructive" class="mt-2">Maior gasto</BaseBadge>
                </div>
              </BaseCard>
              <BaseCard>
                <div class="text-center">
                  <p class="text-sm text-muted-foreground">{{ senadorB.nome_civil }}</p>
                  <p class="mt-1 text-3xl font-bold" :class="totalB <= totalA ? 'text-green-600' : 'text-red-500'">
                    R$ {{ formatCurrency(totalB) }}
                  </p>
                  <BaseBadge v-if="totalA === totalB" variant="secondary" class="mt-2">Empate</BaseBadge>
                  <BaseBadge v-else-if="totalB <= totalA" variant="success" class="mt-2">Menor gasto</BaseBadge>
                  <BaseBadge v-else variant="destructive" class="mt-2">Maior gasto</BaseBadge>
                </div>
              </BaseCard>
            </div>

            <!-- Difference -->
            <BaseCard class="mt-6">
              <div class="text-center">
                <p class="text-sm text-muted-foreground">Diferença de gastos</p>
                <p class="mt-1 text-2xl font-bold text-foreground">
                  R$ {{ formatCurrency(Math.abs(totalA - totalB)) }}
                </p>
                <p class="mt-1 text-sm text-muted-foreground">{{ differenceSummary }}</p>
              </div>
            </BaseCard>
          </div>
        </section>

        <!-- Category Comparison -->
        <section class="py-8">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <h2 class="text-xl font-bold text-foreground mb-6 flex items-center gap-2">
              <BarChart3 class="h-5 w-5 text-primary" />
              Comparação por Categoria
            </h2>

            <BaseCard>
              <div class="space-y-5">
                <div v-if="allCategories.length === 0" class="text-center py-8 text-muted-foreground">
                  Nenhum dado de despesa disponível para comparação.
                </div>
                <div v-for="cat in allCategories" :key="cat" class="space-y-2">
                  <p class="text-sm font-medium text-foreground">{{ cat }}</p>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <!-- Bar A -->
                    <div class="flex items-center gap-3">
                      <span class="text-xs text-muted-foreground w-14 sm:w-20 text-right shrink-0">{{ selectedA?.nome?.split(' ')[0] }}</span>
                      <div class="flex-1 h-6 bg-muted rounded-full overflow-hidden">
                        <div
                          class="h-full bg-primary rounded-full transition-all duration-500 flex items-center justify-end pr-2"
                          :style="{ width: `${getBarWidth(getCategoryValue(categoriasA, cat), cat)}%` }"
                        >
                          <span v-if="getBarWidth(getCategoryValue(categoriasA, cat), cat) > 20" class="text-[10px] font-medium text-primary-foreground">
                            R$ {{ formatCurrencyShort(getCategoryValue(categoriasA, cat)) }}
                          </span>
                        </div>
                      </div>
                      <span v-if="getBarWidth(getCategoryValue(categoriasA, cat), cat) <= 20" class="text-xs text-muted-foreground shrink-0">
                        R$ {{ formatCurrencyShort(getCategoryValue(categoriasA, cat)) }}
                      </span>
                    </div>
                    <!-- Bar B -->
                    <div class="flex items-center gap-3">
                      <span class="text-xs text-muted-foreground w-14 sm:w-20 text-right shrink-0">{{ selectedB?.nome?.split(' ')[0] }}</span>
                      <div class="flex-1 h-6 bg-muted rounded-full overflow-hidden">
                        <div
                          class="h-full bg-accent rounded-full transition-all duration-500 flex items-center justify-end pr-2"
                          :style="{ width: `${getBarWidth(getCategoryValue(categoriasB, cat), cat)}%` }"
                        >
                          <span v-if="getBarWidth(getCategoryValue(categoriasB, cat), cat) > 20" class="text-[10px] font-medium text-accent-foreground">
                            R$ {{ formatCurrencyShort(getCategoryValue(categoriasB, cat)) }}
                          </span>
                        </div>
                      </div>
                      <span v-if="getBarWidth(getCategoryValue(categoriasB, cat), cat) <= 20" class="text-xs text-muted-foreground shrink-0">
                        R$ {{ formatCurrencyShort(getCategoryValue(categoriasB, cat)) }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </BaseCard>
          </div>
        </section>

        <!-- Expenses Table Side by Side -->
        <section class="py-8 bg-muted/30">
          <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <h2 class="text-xl font-bold text-foreground mb-6 flex items-center gap-2">
              <FileText class="h-5 w-5 text-primary" />
              Últimas Despesas
            </h2>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <!-- Table A -->
                <BaseCard variant="elevated">
                <h3 class="font-semibold text-foreground mb-4 flex items-center gap-2">
                  <div class="h-3 w-3 rounded-full bg-primary"></div>
                  {{ senadorA.nome_civil }}
                </h3>
                <div class="overflow-x-auto">
                  <table class="table-professional">
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Tipo</th>
                        <th class="text-right">Valor</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(d, i) in despesasA.slice(0, 8)" :key="i">
                        <td class="whitespace-nowrap">{{ d.mes }}/{{ d.ano }}</td>
                        <td class="truncate max-w-[150px]" :title="d.tipoDespesa">{{ d.tipoDespesa }}</td>
                        <td class="text-right whitespace-nowrap font-medium">R$ {{ d.valor.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) }}</td>
                      </tr>
                      <tr v-if="despesasA.length === 0">
                        <td colspan="3" class="py-6 text-center text-muted-foreground">Sem despesas.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </BaseCard>

              <!-- Table B -->
              <BaseCard variant="elevated">
                <h3 class="font-semibold text-foreground mb-4 flex items-center gap-2">
                  <div class="h-3 w-3 rounded-full bg-accent"></div>
                  {{ senadorB.nome_civil }}
                </h3>
                <div class="overflow-x-auto">
                  <table class="table-professional">
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Tipo</th>
                        <th class="text-right">Valor</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(d, i) in despesasB.slice(0, 8)" :key="i">
                        <td class="whitespace-nowrap">{{ d.mes }}/{{ d.ano }}</td>
                        <td class="truncate max-w-[150px]" :title="d.tipoDespesa">{{ d.tipoDespesa }}</td>
                        <td class="text-right whitespace-nowrap font-medium">R$ {{ d.valor.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) }}</td>
                      </tr>
                      <tr v-if="despesasB.length === 0">
                        <td colspan="3" class="py-6 text-center text-muted-foreground">Sem despesas.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </BaseCard>
            </div>
          </div>
        </section>
      </template>

      <!-- Empty state -->
      <div v-if="!comparisonReady && !loadingComparison" class="py-20 text-center">
        <Scale class="h-16 w-16 mx-auto text-muted-foreground/30" />
        <p class="mt-4 text-lg text-muted-foreground">Selecione dois senadores acima para iniciar a comparação</p>
        <p class="mt-1 text-sm text-muted-foreground/70">As informações serão exibidas lado a lado automaticamente</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Scale, Search, X, UserCheck, DollarSign, BarChart3, FileText, Mail, Calendar } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import { useSenadoStore, type Senador, type SenadorDetail } from '@/stores/senado'
import { absolutizeFoto } from '@/lib/foto'

const store = useSenadoStore()

const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

// Search & selection state
const searchA = ref('')
const searchB = ref('')
const showDropdownA = ref(false)
const showDropdownB = ref(false)
const selectedA = ref<Senador | null>(null)
const selectedB = ref<Senador | null>(null)

// Comparison data
const senadorA = ref<SenadorDetail & { total_gasto: number; categorias: any[] } | null>(null)
const senadorB = ref<SenadorDetail & { total_gasto: number; categorias: any[] } | null>(null)
const despesasA = ref<any[]>([])
const despesasB = ref<any[]>([])
const totalA = ref(0)
const totalB = ref(0)
const loadingComparison = ref(false)
const comparisonReady = ref(false)

// Ensure senadores list is loaded
if (store.filteredSenadores.length === 0) {
  store.fetchSenadores()
}

const normalizeString = (str: string) => {
  return str ? str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase() : ''
}

// Filtered lists for dropdowns
const filteredListA = computed(() => {
  if (!searchA.value || searchA.value.length < 2) return []
  const term = normalizeString(searchA.value)
  return store.filteredSenadores
    .filter(s => normalizeString(s.nome).includes(term))
    .slice(0, 15)
})

const filteredListB = computed(() => {
  if (!searchB.value || searchB.value.length < 2) return []
  const term = normalizeString(searchB.value)
  return store.filteredSenadores
    .filter(s => normalizeString(s.nome).includes(term))
    .slice(0, 15)
})

// Dropdown helpers
const hideDropdown = (side: 'A' | 'B') => {
  setTimeout(() => {
    if (side === 'A') showDropdownA.value = false
    else showDropdownB.value = false
  }, 200)
}

const selectSenador = (side: 'A' | 'B', sen: Senador) => {
  if (side === 'A') {
    selectedA.value = sen
    searchA.value = sen.nome
    showDropdownA.value = false
  } else {
    selectedB.value = sen
    searchB.value = sen.nome
    showDropdownB.value = false
  }
}

const clearSelection = (side: 'A' | 'B') => {
  if (side === 'A') {
    selectedA.value = null
    searchA.value = ''
    senadorA.value = null
    despesasA.value = []
    totalA.value = 0
  } else {
    selectedB.value = null
    searchB.value = ''
    senadorB.value = null
    despesasB.value = []
    totalB.value = 0
  }
  comparisonReady.value = false
}

// Fetch comparison data
const compareSenadores = async () => {
  if (!selectedA.value || !selectedB.value) return

  loadingComparison.value = true
  comparisonReady.value = false

  try {
    const response = await fetch(`${apiUrl}/api/senado/${store.legislatura}/comparar?id1=${selectedA.value.id}&id2=${selectedB.value.id}`)
    
    if (!response.ok) throw new Error('Falha ao obter dados de comparação')
    
    const data = await response.json()
    
    // Adapt the backend structure to the frontend needs
    const buildSenadorEquivalent = (senadorData: any, despesasTotais: any[], fallbackUf?: string) => {
      const minhasDespesas = despesasTotais.filter((d: any) => d.senador === senadorData.codigo)
      const totalGasto = minhasDespesas.reduce((acc: number, curr: any) => acc + curr.total, 0)
      const categorias = minhasDespesas.map((d: any) => ({ categoria: d.tipoDespesa, valor: d.total }))
      
      return {
        ...senadorData,
        id: senadorData.codigo,
        nome_civil: senadorData.nomeCompleto || senadorData.nomeParlamentar,
        nome_parlamentar: senadorData.nomeParlamentar,
        sigla_partido: senadorData.siglaPartido,
        uf: senadorData.uf || fallbackUf || '',
        foto: absolutizeFoto(senadorData.urlFoto),
        total_gasto: totalGasto,
        categorias: categorias
      }
    }

    senadorA.value = buildSenadorEquivalent(data.senador1, data.despesas, selectedA.value?.estado)
    senadorB.value = buildSenadorEquivalent(data.senador2, data.despesas, selectedB.value?.estado)
    
    despesasA.value = data.despesas_recentes_1 || []
    despesasB.value = data.despesas_recentes_2 || []
    
    totalA.value = senadorA.value?.total_gasto || 0
    totalB.value = senadorB.value?.total_gasto || 0
    
    comparisonReady.value = true
  } catch (e) {
    console.error('Erro ao comparar senadores:', e)
    alert('Erro ao carregar dados de comparação. Por favor, tente novamente. Dica: Os senadores devem ser diferentes.')
  } finally {
    loadingComparison.value = false
  }
}

// Category comparison helpers
interface CatEntry { categoria: string; valor: number }

const categoriasA = computed<CatEntry[]>(() => senadorA.value?.categorias || [])
const categoriasB = computed<CatEntry[]>(() => senadorB.value?.categorias || [])

const allCategories = computed(() => {
  const set = new Set<string>()
  categoriasA.value.forEach(c => set.add(c.categoria))
  categoriasB.value.forEach(c => set.add(c.categoria))
  
  // Sort by combined value descending
  return [...set].sort((a, b) => {
    const va = getCategoryValue(categoriasA.value, a) + getCategoryValue(categoriasB.value, a)
    const vb = getCategoryValue(categoriasA.value, b) + getCategoryValue(categoriasB.value, b)
    return vb - va
  }).slice(0, 8) // Limit to top 8 common categories for UI neatness
})

const getCategoryValue = (cats: CatEntry[], name: string): number => {
  return cats.find(c => c.categoria === name)?.valor || 0
}

const getBarWidth = (value: number, category: string): number => {
  const maxVal = Math.max(
    getCategoryValue(categoriasA.value, category),
    getCategoryValue(categoriasB.value, category)
  )
  if (maxVal === 0) return 0
  return Math.max(2, (value / maxVal) * 100)
}

// Formatting helpers
const formatDate = (dateString: string) => {
  if (!dateString) return '--'
  return new Date(dateString).toLocaleDateString('pt-BR')
}

const formatCurrency = (value: number): string => {
  return value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatCurrencyShort = (value: number): string => {
  if (value >= 1000000) return `${(value / 1000000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
  if (value >= 1000) return `${(value / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`
  return value.toLocaleString('pt-BR')
}

const percentDiff = computed(() => {
  const min = Math.min(totalA.value, totalB.value)
  if (min <= 0) return null
  return (((Math.abs(totalA.value - totalB.value)) / min) * 100).toFixed(1)
})

const differenceSummary = computed(() => {
  if (!senadorA.value || !senadorB.value) return ''

  if (totalA.value === totalB.value) {
    return 'Os dois tiveram o mesmo total de gastos.'
  }

  const senadorMaiorGasto = totalA.value > totalB.value ? senadorA.value.nome_civil : senadorB.value.nome_civil
  const senadorMenorGasto = totalA.value > totalB.value ? senadorB.value.nome_civil : senadorA.value.nome_civil

  if (percentDiff.value === null) {
    return `${senadorMaiorGasto} registrou despesas, enquanto ${senadorMenorGasto} não teve gastos no período selecionado.`
  }

  return `${senadorMaiorGasto} gastou ${percentDiff.value}% a mais.`
})
</script>
