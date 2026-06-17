<template>
  <BaseCard>
    <div class="p-6">
      <h3 class="text-lg font-semibold mb-4">Emendas Recentes</h3>
      
      <!-- Loading State -->
      <BaseLoading v-if="carregando" message="Carregando emendas..." />

      <!-- Empty State -->
      <div v-else-if="emendas.length === 0" class="text-center py-4 text-muted-foreground">
        Nenhuma emenda encontrada.
      </div>

      <!-- Real Data -->
      <div v-else class="space-y-4">
        <div v-for="emenda in emendas" :key="emenda.codigo" class="flex items-start gap-4 pb-4 border-b last:border-0">
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <h4 class="font-semibold">{{ emenda.funcao || 'Atividade Legislativa' }}</h4>
              <BaseBadge :variant="emenda.valorPago > 0 ? 'success' : 'warning'">
                {{ emenda.valorPago > 0 ? 'Paga' : 'Empenhada' }}
              </BaseBadge>
            </div>
            <p class="text-sm text-muted-foreground mb-2">{{ emenda.tipo }} (Código: {{ emenda.codigo }})</p>
            <div class="flex items-center gap-4 text-sm text-muted-foreground flex-wrap">
              <span>Autor: <span class="font-medium text-foreground uppercase">{{ emenda.deputado }}</span></span>
              <span>•</span>
              <span>{{ emenda.localidade || 'Brasil' }}</span>
              <span>•</span>
              <span>Ano: {{ emenda.ano }}</span>
            </div>
          </div>
          <div class="text-right">
            <p class="font-semibold text-lg text-accent">
              R$ {{ formataValor(emenda.valorPago > 0 ? emenda.valorPago : emenda.valorEmpenhado) }}
            </p>
          </div>
        </div>
      </div>
      
      <!-- Load More Button -->
      <div v-if="!carregando && emendas.length > 0" class="mt-6 text-center">
        <button 
          @click="carregarMais" 
          :disabled="carregandoMais"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background border border-input hover:bg-accent hover:text-accent-foreground h-10 py-2 px-4"
        >
          <span v-if="carregandoMais">...</span>
          <span v-else>Carregar Mais</span>
        </button>
      </div>

    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'
import { useCamaraStore } from '@/stores/camara'
import { storeToRefs } from 'pinia'

const store = useCamaraStore()
const { legislatura, filters } = storeToRefs(store)

// Teria que ser tipado com uma interface correta, mas any resolve por hora
const emendas = ref<any[]>([])
const carregando = ref(true)
const carregandoMais = ref(false)
const paginaAtual = ref(1)

// URL base da sua API
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Função que busca do backend Python
async function carregarEmendas(pagina = 1) {
  if (pagina === 1) {
    carregando.value = true
  } else {
    carregandoMais.value = true
  }

  try {
    const busca = filters.value.search || ''
    const response = await fetch(`${API_URL}/api/camara/${legislatura.value}/emendas?pagina=${pagina}&busca=${busca}`)
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const dados = await response.json()
    const listaEmendas = dados.emendas || []
    
    if (pagina === 1) {
      emendas.value = listaEmendas
    } else {
      emendas.value.push(...listaEmendas)
    }
    
  } catch (erro) {
    console.error('Erro ao buscar emendas da API:', erro)
  } finally {
    carregando.value = false
    carregandoMais.value = false
  }
}

function carregarMais() {
    paginaAtual.value++
    carregarEmendas(paginaAtual.value)
}

function formataValor(valor: number) {
  if (!valor) return '0,00';
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Quando o componente for montado na tela, chama a função para a página 1
onMounted(() => {
  carregarEmendas(1)
})
</script>
