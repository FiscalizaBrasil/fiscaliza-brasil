<template>
  <section class="py-8 bg-muted/30">
    <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <BaseCard>
          <div class="flex items-center gap-4">
            <div class="p-3 rounded-xl bg-primary/10">
              <FileText class="h-6 w-6 text-primary" />
            </div>
            <div>
              <p class="text-sm text-muted-foreground">Total de Projetos Legislativos</p>
              <p class="text-2xl font-bold text-foreground">{{ store.totalProjetosLegislativos.toLocaleString('pt-BR') }}</p>
            </div>
          </div>
        </BaseCard>

        <BaseCard>
          <div class="flex items-center gap-4">
            <div class="p-3 rounded-xl bg-accent/10">
              <BarChart3 class="h-6 w-6 text-accent" />
            </div>
            <div>
              <p class="text-sm text-muted-foreground">Tipos Diferentes</p>
              <p class="text-2xl font-bold text-foreground">{{ store.projetosLegislativosPorTipo.length }}</p>
            </div>
          </div>
        </BaseCard>

        <BaseCard class="sm:col-span-2 lg:col-span-1">
          <div class="flex items-center gap-4">
            <div class="p-3 rounded-xl bg-chart-2/10">
              <TrendingUp class="h-6 w-6 text-chart-2" />
            </div>
            <div>
              <p class="text-sm text-muted-foreground">Tipo Mais Frequente</p>
              <p class="text-2xl font-bold text-foreground">
                {{ store.projetosLegislativosPorTipo.length > 0 ? store.projetosLegislativosPorTipo[0].tipo : '--' }}
              </p>
            </div>
          </div>
        </BaseCard>
      </div>

      <!-- Distribuição por Tipo -->
      <div v-if="store.projetosLegislativosPorTipo.length > 0" class="mt-6">
        <h3 class="text-lg font-semibold text-foreground mb-4">Distribuição por Tipo</h3>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div
            v-for="tipo in store.projetosLegislativosPorTipo"
            :key="tipo.tipo"
            class="flex items-center justify-between p-3 rounded-lg bg-background border border-border"
          >
            <div class="flex items-center gap-3">
              <BaseBadge variant="outline">{{ tipo.tipo }}</BaseBadge>
              <span class="text-sm text-foreground">{{ getTipoNome(tipo.tipo) }}</span>
            </div>
            <span class="text-sm font-semibold text-foreground">{{ tipo.quantidade }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { FileText, BarChart3, TrendingUp } from 'lucide-vue-next'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import { useCamaraStore } from '@/stores/camara'

const store = useCamaraStore()

const tiposNomes: Record<string, string> = {
  PL: 'Projeto de Lei',
  PLP: 'Projeto de Lei Complementar',
  PEC: 'Proposta de Emenda à Constituição',
  MPV: 'Medida Provisória',
  PDL: 'Projeto de Decreto Legislativo',
  PRC: 'Projeto de Resolução',
  REQ: 'Requerimento',
  INC: 'Indicação',
  RIC: 'Requerimento de Informação',
}

const getTipoNome = (sigla: string) => {
  return tiposNomes[sigla] || sigla
}
</script>
