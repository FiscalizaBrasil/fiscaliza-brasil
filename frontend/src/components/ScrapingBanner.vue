<template>
  <div v-if="showBanner" class="bg-amber-50 border-l-4 border-amber-400 p-4 mb-6 rounded-r-lg shadow-sm">
    <div class="flex items-start">
      <div class="flex-shrink-0">
        <svg class="h-5 w-5 text-amber-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
      </div>
      <div class="ml-3 flex-1">
        <p class="text-sm text-amber-700">
          <span class="font-medium">Dados em carregamento!</span>
          Os dados deste parlamentar estão sendo baixados em segundo plano.
          As informações serão atualizadas automaticamente em até 15 segundos.
        </p>
        <div class="mt-2 flex items-center gap-4 text-xs text-amber-600">
          <span v-if="tipo === 'camara' && camaraPendentes !== null" class="inline-flex items-center gap-1">
            <svg class="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Deputados pendentes: {{ camaraPendentes }}
          </span>
          <span v-if="tipo === 'senado' && senadoPendentes !== null" class="inline-flex items-center gap-1">
            <svg class="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Senadores pendentes: {{ senadoPendentes }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"

const props = defineProps<{
  tipo: "camara" | "senado"
  emAndamento: boolean
  camaraPendentes?: number | null
  senadoPendentes?: number | null
}>()

const showBanner = computed(() => props.emAndamento)
</script>
