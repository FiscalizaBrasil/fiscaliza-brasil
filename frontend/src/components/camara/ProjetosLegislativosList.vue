<template>
  <div>
    <!-- Results count -->
    <p class="text-sm text-muted-foreground mb-4">
      {{ store.totalProjetosLegislativos.toLocaleString('pt-BR') }} projetos legislativos encontrados
    </p>

    <BaseLoading v-if="store.loadingProjetosLegislativos && store.projetosLegislativosList.length === 0" message="Carregando projetos legislativos..." />

    <!-- Error State -->
    <div v-else-if="store.error" class="text-center py-12">
      <p class="text-destructive">{{ store.error }}</p>
    </div>

    <!-- Lista -->
    <div v-else class="space-y-4">
      <div
        v-for="projeto in store.projetosLegislativosList"
        :key="projeto.id"
      >
        <BaseCard
          hover
          class="overflow-hidden cursor-pointer transition-all duration-200"
          :class="{ 'ring-2 ring-primary/50': store.selectedProjetoLegislativoId === projeto.id }"
          @click="store.toggleProjetoLegislativoVotos(projeto.id)"
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
                v-if="projeto.url_inteiro_teor"
                :href="projeto.url_inteiro_teor"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1 text-sm text-primary hover:underline group bg-primary/10 px-2 py-1 rounded-md transition-colors"
                @click.stop
              >
                <FileText class="h-4 w-4 sm:h-3 sm:w-3 transition-transform group-hover:scale-110" />
                <span class="hidden sm:inline font-medium">Inteiro Teor</span>
              </a>
              <a
                :href="`https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=${projeto.id}`"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1 text-sm text-primary hover:underline group"
                @click.stop
              >
                <span class="hidden sm:inline">Ver na Câmara</span>
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
          <BaseLoading v-if="store.loadingVotos" message="Buscando votos..." />

          <!-- Sem votos -->
          <div
            v-else-if="store.currentVotos && store.currentVotos.historico_votacoes.length === 0"
            class="py-8 text-center"
          >
            <Vote class="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p class="text-sm text-muted-foreground">Sem votos nominais registrados para este projeto legislativo.</p>
          </div>

          <!-- Lista de Votações (Accordion) -->
          <div v-else-if="store.currentVotos" class="divide-y divide-border">
            <div
              v-for="votacao in store.currentVotos.historico_votacoes"
              :key="votacao.id_votacao"
              class="transition-colors hover:bg-muted/10"
            >
              <!-- Header da Votação (Clicável) -->
              <button
                @click="toggleVotacao(votacao.id_votacao)"
                class="w-full text-left p-4 flex items-start gap-3 focus:outline-none focus:bg-muted/20"
              >
                <ChevronRight
                  class="h-5 w-5 text-muted-foreground mt-0.5 transition-transform duration-200 flex-shrink-0"
                  :class="{ 'rotate-90': expandedVotacaoIds.has(votacao.id_votacao) }"
                />
                
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between gap-4 mb-2 flex-wrap">
                    <p class="text-sm font-medium text-foreground line-clamp-2">{{ votacao.descricao || 'Votação' }}</p>
                    <BaseBadge variant="outline" class="flex-shrink-0">{{ votacao.total_votos }} votos</BaseBadge>
                  </div>
                  
                  <div class="flex items-center gap-2 mb-2">
                     <span class="text-xs text-muted-foreground">{{ formatDateTime(votacao.data) }}</span>
                  </div>

                  <!-- Resumo (Sempre visível) -->
                  <div class="flex flex-wrap gap-2">
                    <span
                      v-for="(count, tipo) in getVotosSummary(votacao.lista_votos)"
                      :key="tipo"
                      class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border"
                      :class="getVotoBadgeClass(tipo as string)"
                    >
                      {{ tipo }}: {{ count }}
                    </span>
                  </div>
                </div>
              </button>

              <!-- Tabela de votos (Expansível) -->
              <div
                v-if="expandedVotacaoIds.has(votacao.id_votacao)"
                class="px-4 pb-4 pl-12 animate-slideDown"
              >
                <div class="max-h-60 overflow-y-auto overflow-x-auto rounded-lg border border-border">
                  <table class="table-professional w-full">
                    <thead>
                      <tr>
                        <th class="w-12 text-center px-4 py-2">Foto</th>
                        <th class="whitespace-nowrap px-4 py-2 text-left">Deputado(a)</th>
                        <th class="text-center w-24 sm:w-32 whitespace-nowrap px-4 py-2">Voto</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="voto in votacao.lista_votos" :key="voto.deputado_id">
                        <td class="text-center px-4 py-2">
                          <div class="flex justify-center">
                            <img 
                              :src="`https://www.camara.leg.br/internet/deputado/bandep/${voto.deputado_id}.jpg`" 
                              :alt="voto.nome"
                              class="h-8 w-8 rounded-full object-cover border border-border"
                              loading="lazy"
                            />
                          </div>
                        </td>
                        <td class="px-4 py-2">
                          <a :href="`/camara/deputados/${voto.deputado_id}`" target="_blank" class="text-foreground border-b border-transparent hover:border-foreground transition-colors cursor-pointer font-medium">
                            {{ voto.nome }}
                          </a>
                        </td>
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
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!store.loadingProjetosLegislativos && !store.error && store.projetosLegislativosList.length === 0" class="text-center py-12">
      <FileText class="h-12 w-12 text-muted-foreground mx-auto mb-4" />
      <p class="text-muted-foreground">Nenhum projeto legislativo encontrado com os filtros selecionados.</p>
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
import { onMounted, ref, watch } from 'vue'
import { FileText, User, ExternalLink, ChevronDown, Vote, ChevronRight } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import { useCamaraStore } from '@/stores/camara'
import type { VotoDeputado } from '@/stores/camara'

const store = useCamaraStore()
const expandedVotacaoIds = ref<Set<string>>(new Set())

onMounted(() => {
  if (store.projetosLegislativosList.length === 0) {
    store.fetchProjetosLegislativos(1)
  }
})

// Watch for changes in current votes to expand the first one by default
watch(() => store.currentVotos, (newVotos) => {
  expandedVotacaoIds.value.clear()
  if (newVotos && newVotos.historico_votacoes.length > 0) {
    // Expand the first (most recent) voting by default
    expandedVotacaoIds.value.add(newVotos.historico_votacoes[0].id_votacao)
  }
})

const toggleVotacao = (id: string) => {
  if (expandedVotacaoIds.value.has(id)) {
    expandedVotacaoIds.value.delete(id)
  } else {
    expandedVotacaoIds.value.add(id)
  }
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

const formatDateTime = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getVotosSummary = (votos: VotoDeputado[]) => {
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
