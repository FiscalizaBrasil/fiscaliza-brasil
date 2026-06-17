<template>
  <div>
    <!-- Results count -->
    <p class="text-sm text-muted-foreground mb-4">
      {{ store.totalProjetosLegislativos.toLocaleString('pt-BR') }} projetos legislativos encontrados
    </p>

    <!-- Loading -->
    <div v-if="store.loadingProjetosLegislativos && store.projetosLegislativosList.length === 0" class="py-12">
      <div class="space-y-4">
        <div v-for="i in 3" :key="i" class="card-default p-6">
          <div class="flex items-start gap-4">
            <div class="skeleton-rect h-12 w-12 flex-shrink-0"></div>
            <div class="flex-1 space-y-2">
              <div class="flex gap-2">
                <div class="skeleton-text w-24"></div>
                <div class="skeleton-text-sm w-16"></div>
              </div>
              <div class="skeleton-text w-full"></div>
              <div class="skeleton-text w-3/4"></div>
              <div class="skeleton-text-sm w-32 mt-2"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="store.error" class="text-center py-12">
      <p class="text-destructive">{{ store.error }}</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="!store.loadingProjetosLegislativos && store.filteredProjetosLegislativos.length === 0" class="text-center py-12">
      <FileText class="h-12 w-12 text-muted-foreground mx-auto mb-4" />
      <p class="text-muted-foreground">Nenhum projeto legislativo encontrado com os filtros atuais.</p>
    </div>

    <!-- Lista -->
    <div v-else class="space-y-4">
      <div
        v-for="projeto in store.filteredProjetosLegislativos"
        :key="projeto.id"
      >
        <BaseCard
          hover
          class="overflow-hidden cursor-pointer transition-all duration-200"
          :class="{ 'ring-2 ring-primary/50': store.selectedProjetoLegislativoId === projeto.id }"
          @click="handleProjetoClick(projeto.id)"
        >
          <div class="flex items-start gap-3 sm:gap-4">
            <div class="flex-shrink-0 flex items-center justify-center h-10 w-10 sm:h-12 sm:w-12 rounded-lg bg-primary/10">
              <FileText class="h-5 w-5 sm:h-6 sm:w-6 text-primary" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1 flex-wrap">
                <BaseBadge>{{ projeto.siglaTipo }} {{ projeto.numero }}/{{ projeto.ano }}</BaseBadge>
                <span v-if="projeto.dataApresentacao" class="text-xs text-muted-foreground">
                  {{ formatDate(projeto.dataApresentacao) }}
                </span>
              </div>
              <p class="text-sm text-foreground line-clamp-2">{{ projeto.ementa }}</p>
              <div class="flex items-center gap-2 mt-2">
                <User class="h-3 w-3 text-muted-foreground" />
                <span class="text-xs text-muted-foreground">{{ projeto.autor_principal }}</span>
              </div>
            </div>
            <div class="flex items-center gap-2 sm:gap-3 flex-shrink-0">
              <a
                :href="`https://www25.senado.leg.br/web/atividade/materias/-/materia/${projeto.id}`"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1 text-sm text-primary hover:underline group"
                @click.stop
              >
                <span class="hidden sm:inline">Ver no Senado</span>
                <ExternalLink class="h-4 w-4 sm:h-3 sm:w-3 transition-transform group-hover:translate-x-0.5" />
              </a>
              <ChevronDown
                class="h-4 w-4 text-muted-foreground transition-transform duration-200"
                :class="{ 'rotate-180': store.selectedProjetoLegislativoId === projeto.id }"
              />
            </div>
          </div>
        </BaseCard>

        <!-- Painel de Votos Expansível -->
        <div
          v-if="store.selectedProjetoLegislativoId === projeto.id"
          class="mt-1 rounded-lg border border-border bg-muted overflow-hidden animate-slideDown"
        >
          <!-- Loading votos -->
          <div v-if="store.loadingVotos" class="py-8 text-center">
            <div class="inline-flex items-center gap-2 text-muted-foreground">
              <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Buscando votos...
            </div>
          </div>

          <!-- Sem votos -->
          <div
            v-else-if="store.currentVotos && store.currentVotos.votacao.length === 0"
            class="py-8 text-center"
          >
            <Vote class="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p class="text-sm text-muted-foreground">Sem votos nominais registrados para este projeto legislativo.</p>
          </div>

          <!-- Tabela de votos -->
          <div v-else-if="store.currentVotos" class="p-4">
            <!-- Busca por senador -->
            <div class="relative mb-4">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <input
                type="text"
                placeholder="Buscar senador(a) por nome, partido ou UF..."
                v-model="votosSearch"
                class="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-background text-foreground text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent"
              />
            </div>

            <!-- Resumo de votos -->
            <div class="flex flex-wrap gap-2 mb-4">
              <span
                v-for="(count, tipo) in getVotosSummary(filteredVotos)"
                :key="tipo"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border"
                :class="getVotoBadgeClass(tipo as string)"
              >
                {{ tipo }}: {{ count }}
              </span>
              <span class="text-xs text-muted-foreground self-center">
                {{ filteredVotos.length }} de {{ totalVotos }} senadores
              </span>
            </div>

            <div class="max-h-60 overflow-y-auto rounded-lg border border-border">
              <table class="table-professional">
                <thead>
                  <tr>
                    <th class="w-12 text-center px-4 py-2">Foto</th>
                    <th class="whitespace-nowrap px-4 py-2 text-left">Senador(a)</th>
                    <th class="text-center w-32 px-4 py-2">Partido</th>
                    <th class="text-center w-20 px-4 py-2">UF</th>
                    <th class="text-center w-32 px-4 py-2">Voto</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="filteredVotos.length === 0">
                    <td colspan="5" class="text-center text-muted-foreground py-4">
                      Nenhum senador encontrado com "{{ votosSearch }}"
                    </td>
                  </tr>
                  <tr v-for="(voto, idx) in filteredVotos" :key="idx">
                    <td class="text-center px-4 py-2">
                      <div class="flex justify-center">
                        <img 
                          :src="voto.foto || '/placeholder-user.svg'" 
                          :alt="voto.nomeParlamentar"
                          class="h-8 w-8 rounded-full object-cover border border-border"
                          loading="lazy"
                        />
                      </div>
                    </td>
                    <td class="px-4 py-2">
                      <a :href="voto.codigo ? `/senado/senadores/${voto.codigo}` : '#'" :target="voto.codigo ? '_blank' : undefined" class="text-foreground border-b border-transparent hover:border-foreground transition-colors cursor-pointer font-medium">
                        {{ voto.nomeParlamentar }}
                      </a>
                    </td>
                    <td class="text-center px-4 py-2">{{ voto.siglaPartido }}</td>
                    <td class="text-center px-4 py-2">{{ voto.uf }}</td>
                    <td class="text-center px-4 py-2">
                      <span
                        class="inline-block px-2 py-0.5 rounded-full text-xs font-medium border"
                        :class="getVotoBadgeClass(voto.voto)"
                      >
                        {{ voto.voto }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Load more -->
    <div v-if="store.hasMoreProjetosLegislativos && store.projetosLegislativosList.length > 0" class="flex justify-center mt-8">
      <button
        @click="store.loadMoreProjetosLegislativos()"
        class="px-6 py-3 rounded-lg border border-border bg-background text-foreground font-medium hover:bg-muted transition-colors inline-flex items-center gap-2"
      >
        <span>Carregar mais</span>
        <ChevronDown class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { FileText, User, ExternalLink, ChevronDown, Vote, Search } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import { useSenadoStore } from '@/stores/senado'
import type { VotoSenador } from '@/stores/senado'

const store = useSenadoStore()
const votosSearch = ref('')

const hiddenVotoTypes = ['P-NRV', 'AP', 'Presidente (art. 51 RISF)', 'LS', 'NCom']

const totalVotos = computed(() => {
  if (!store.currentVotos) return 0
  return store.currentVotos.votacao.filter(v => !hiddenVotoTypes.includes(v.voto)).length
})

const handleProjetoClick = (id: number) => {
  votosSearch.value = ''
  store.toggleProjetoLegislativoVotos(id)
}

const filteredVotos = computed(() => {
  if (!store.currentVotos) return []
  const base = store.currentVotos.votacao.filter(v => !hiddenVotoTypes.includes(v.voto))
  if (!votosSearch.value.trim()) return base

  const search = votosSearch.value.toLowerCase().trim()
  return base.filter(v =>
    v.nomeParlamentar.toLowerCase().includes(search) ||
    v.siglaPartido.toLowerCase().includes(search) ||
    v.uf.toLowerCase().includes(search)
  )
})

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

const getVotosSummary = (votos: VotoSenador[]) => {
  const summary: Record<string, number> = {}
  votos.forEach(v => {
    summary[v.voto] = (summary[v.voto] || 0) + 1
  })
  return summary
}

const getVotoBadgeClass = (voto: string) => {
  const v = voto.toLowerCase()
  if (v === 'sim') return 'bg-green-600 text-white border-green-700 dark:bg-green-700 dark:text-white dark:border-green-800 border'
  if (v.includes('não') || v === 'nao') return 'bg-red-600 text-white border-red-700 dark:bg-red-700 dark:text-white dark:border-red-800 border'
  if (v.includes('abstenção') || v.includes('abstencao')) return 'bg-gray-900 text-white border-gray-950 dark:bg-gray-700 dark:text-white dark:border-gray-600 border'
  if (v.includes('obstrução') || v.includes('obstrucao')) return 'bg-orange-600 text-white border-orange-700 dark:bg-orange-700 dark:text-white dark:border-orange-800 border'
  return 'bg-slate-600 text-white border-slate-700 dark:bg-slate-700 dark:text-white dark:border-slate-600 border'
}
</script>

<style scoped>
.animate-slideDown {
  animation: slideDown 0.35s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

@keyframes slideDown {
  from {
    opacity: 0;
    max-height: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    max-height: 2000px;
    transform: translateY(0);
  }
}
</style>
