<template>
  <BaseCard>
    <div class="p-6">
      <h3 class="text-lg font-semibold mb-4">Despesas por Categoria</h3>
      <div class="space-y-3">
        <div v-for="categoria in categorias" :key="categoria.nome" class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="h-10 w-10 rounded-full flex items-center justify-center" :style="{ backgroundColor: categoria.cor + '20' }">
              <span :style="{ color: categoria.cor }">{{ categoria.icon }}</span>
            </div>
            <div>
              <p class="font-medium">{{ categoria.nome }}</p>
              <p class="text-sm text-muted-foreground">{{ categoria.quantidade }} lançamentos</p>
            </div>
          </div>
          <div class="text-right">
            <p class="font-semibold">{{ categoria.valor }}</p>
            <p class="text-sm text-muted-foreground">{{ categoria.percentual }}%</p>
          </div>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'

const categorias = ref([
  { nome: 'Divulgação', valor: 'R$ 45.2M', percentual: '36.0', quantidade: 15234, cor: '#3b82f6', icon: '📢' },
  { nome: 'Passagens', valor: 'R$ 28.5M', percentual: '22.7', quantidade: 8945, cor: '#10b981', icon: '✈️' },
  { nome: 'Combustível', valor: 'R$ 18.3M', percentual: '14.6', quantidade: 12456, cor: '#f59e0b', icon: '⛽' },
  { nome: 'Escritório', valor: 'R$ 15.8M', percentual: '12.6', quantidade: 5678, cor: '#8b5cf6', icon: '🏢' },
  { nome: 'Telefonia', valor: 'R$ 10.2M', percentual: '8.1', quantidade: 2341, cor: '#ec4899', icon: '📱' },
  { nome: 'Outros', valor: 'R$ 7.4M', percentual: '6.0', quantidade: 580, cor: '#6b7280', icon: '📦' },
])
</script>
