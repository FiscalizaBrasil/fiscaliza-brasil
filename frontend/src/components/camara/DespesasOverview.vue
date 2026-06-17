<template>
  <div class="space-y-6">
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <BaseCard>
        <div class="p-6">
          <div class="text-sm font-medium text-muted-foreground">Total de Despesas</div>
          <div class="text-2xl font-bold">R$ 125.4M</div>
          <p class="text-xs text-muted-foreground mt-1">+20.1% em relação ao mês anterior</p>
        </div>
      </BaseCard>
      <BaseCard>
        <div class="p-6">
          <div class="text-sm font-medium text-muted-foreground">Média por Deputado</div>
          <div class="text-2xl font-bold">R$ 244.2K</div>
          <p class="text-xs text-muted-foreground mt-1">+12.5% em relação ao mês anterior</p>
        </div>
      </BaseCard>
      <BaseCard>
        <div class="p-6">
          <div class="text-sm font-medium text-muted-foreground">Maior Despesa</div>
          <div class="text-2xl font-bold">R$ 1.2M</div>
          <p class="text-xs text-muted-foreground mt-1">Divulgação parlamentar</p>
        </div>
      </BaseCard>
      <BaseCard>
        <div class="p-6">
          <div class="text-sm font-medium text-muted-foreground">Total de Lançamentos</div>
          <div class="text-2xl font-bold">45,234</div>
          <p class="text-xs text-muted-foreground mt-1">+5.2% em relação ao mês anterior</p>
        </div>
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import BaseCard from '@/components/ui/BaseCard.vue'
</script>
