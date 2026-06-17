<template>
  <div class="space-y-6">
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <BaseCard>
        <div class="p-6">
          <div class="text-sm font-medium text-muted-foreground">Total de Emendas</div>
          <div class="text-2xl font-bold">R$ 18.5B</div>
          <p class="text-xs text-muted-foreground mt-1">Orçamento 2024</p>
        </div>
      </BaseCard>
      <BaseCard>
        <div class="p-6">
          <div class="text-sm font-medium text-muted-foreground">Emendas Aprovadas</div>
          <div class="text-2xl font-bold">12,345</div>
          <p class="text-xs text-muted-foreground mt-1">78% do total</p>
        </div>
      </BaseCard>
      <BaseCard>
        <div class="p-6">
          <div class="text-sm font-medium text-muted-foreground">Média por Deputado</div>
          <div class="text-2xl font-bold">R$ 36.0M</div>
          <p class="text-xs text-muted-foreground mt-1">Por deputado</p>
        </div>
      </BaseCard>
      <BaseCard>
        <div class="p-6">
          <div class="text-sm font-medium text-muted-foreground">Municípios Beneficiados</div>
          <div class="text-2xl font-bold">4,832</div>
          <p class="text-xs text-muted-foreground mt-1">87% dos municípios</p>
        </div>
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import BaseCard from '@/components/ui/BaseCard.vue'
</script>
