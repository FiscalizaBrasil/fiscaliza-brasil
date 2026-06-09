<template>
  <section class="py-12 bg-muted/30">
    <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <!-- Aviso de banco vazio -->
      <div v-if="dbVazio" class="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm">
        <p class="font-medium">Carregando dados iniciais...</p>
        <p class="mt-1">A lista de deputados e senadores está sendo carregada a partir da última legislatura. Os dados serão exibidos em breve.</p>
      </div>

      <div class="grid grid-cols-2 gap-4 lg:grid-cols-4 lg:gap-6">
        <BaseCard
          v-for="metric in metrics"
          :key="metric.id"
          variant="flat"
          class="hover:border-primary/20"
        >
          <div v-if="loading">
            <div class="animate-pulse flex flex-col gap-2">
              <div class="h-4 w-20 bg-muted rounded"></div>
              <div class="h-8 w-24 bg-muted rounded"></div>
              <div class="h-3 w-16 bg-muted rounded"></div>
            </div>
          </div>
          <div v-else>
            <p class="text-sm text-muted-foreground">{{ metric.label }}</p>
            <p class="mt-1 text-2xl font-bold text-foreground">{{ metric.value }}</p>
            <p class="text-xs text-muted-foreground mt-1">{{ metric.description }}</p>
          </div>
        </BaseCard>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import { formatCurrency } from '@/utils/format'

const deputadosTotal = ref<number | null>(null)
const senadoresTotal = ref<number | null>(null)
const gastosCamara = ref<number | null>(null)
const gastosSenado = ref<number | null>(null)
const dbVazio = ref(false)

const loading = ref(true)

let pollingTimer: ReturnType<typeof setInterval> | null = null
const POLLING_INTERVAL = 5000 // 5 segundos
const POLLING_TIMEOUT = 180000 // 3 minutos (aumentado para dar tempo do download prioritário)

const apiUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

async function fetchResumoPrincipal() {
  try {
    const [camaraRes, senadoRes] = await Promise.all([
      fetch(`${apiUrl}/api/camara/resumo-principal?legislatura=0`),
      fetch(`${apiUrl}/api/senado/resumo-principal?legislatura=0`)
    ])
    
    let algumVazio = false
    let gastosPendentes = false
    
    if (camaraRes.ok) {
      const data = await camaraRes.json()
      deputadosTotal.value = data.total_parlamentares
      gastosCamara.value = data.gastos_12_meses
      if (data.db_vazio) algumVazio = true
      // Se tem deputados mas gastos ainda são 0, continua polling
      if (!data.db_vazio && data.total_parlamentares > 0 && data.gastos_12_meses === 0) {
        gastosPendentes = true
      }
    }
    
    if (senadoRes.ok) {
      const data = await senadoRes.json()
      senadoresTotal.value = data.total_parlamentares
      gastosSenado.value = data.gastos_12_meses
      if (data.db_vazio) algumVazio = true
      // Se tem senadores mas gastos ainda são 0, continua polling
      if (!data.db_vazio && data.total_parlamentares > 0 && data.gastos_12_meses === 0) {
        gastosPendentes = true
      }
    }
    
    dbVazio.value = algumVazio
    
    // Para o polling apenas quando ambos os dados estiverem completos
    // (banco não vazio E gastos > 0 para ambas as casas)
    if (!algumVazio && !gastosPendentes && pollingTimer) {
      clearInterval(pollingTimer)
      pollingTimer = null
    }
  } catch (err) {
    console.error("Erro ao buscar resumo principal:", err)
  } finally {
    loading.value = false
  }
}

function iniciarPolling() {
  // Polling a cada 5s enquanto os dados não estiverem completos
  pollingTimer = setInterval(fetchResumoPrincipal, POLLING_INTERVAL)
  
  // Timeout de segurança: para o polling após 3 minutos
  setTimeout(() => {
    if (pollingTimer) {
      clearInterval(pollingTimer)
      pollingTimer = null
    }
  }, POLLING_TIMEOUT)
}

onMounted(async () => {
  loading.value = true
  await fetchResumoPrincipal()
  
  // Inicia polling se o banco estiver vazio OU se gastos ainda forem 0
  if (dbVazio.value || gastosCamara.value === 0 || gastosSenado.value === 0) {
    iniciarPolling()
  }
})

onUnmounted(() => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
})

const metrics = computed(() => [
  {
    id: 1,
    label: "Deputados",
    value: deputadosTotal.value !== null ? deputadosTotal.value : "--",
    description: "Câmara dos Deputados",
  },
  {
    id: 2,
    label: "Senadores",
    value: senadoresTotal.value !== null ? senadoresTotal.value : "--",
    description: "Senado Federal",
  },
  {
    id: 3,
    label: "Gastos Câmara",
    value: formatCurrency(gastosCamara.value),
    description: "Últimos 12 meses",
  },
  {
    id: 4,
    label: "Gastos Senado",
    value: formatCurrency(gastosSenado.value),
    description: "Últimos 12 meses",
  }
])
</script>
