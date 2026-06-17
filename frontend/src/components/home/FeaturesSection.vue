<template>
  <section class="py-16 bg-muted/30">
    <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <h2 class="text-2xl font-bold text-foreground mb-8">Explore os Dados</h2>

      <div class="grid gap-6 lg:grid-cols-2">
        <!-- Câmara dos Deputados -->
        <div class="bg-card rounded-lg border border-border p-6 shadow-sm">
          <div class="flex items-center gap-3 mb-6">
            <div class="p-2 rounded-md bg-primary/10">
              <Building2 class="h-6 w-6 text-primary" />
            </div>
            <div>
              <h3 class="text-xl font-bold text-foreground">Câmara dos Deputados</h3>
           
            </div>
          </div>
          
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <router-link
              v-for="item in camaraItems"
              :key="item.href"
              :to="item.href"
              class="group flex items-center justify-between p-4 rounded-lg bg-muted/50 hover:bg-muted border border-border/50 hover:border-primary/20 transition-all duration-200"
            >
              <div class="flex items-center gap-4">
                <div class="p-2 rounded-md bg-background text-muted-foreground group-hover:text-primary transition-colors">
                  <component :is="item.icon" class="h-5 w-5" />
                </div>
                <div>
                  <p class="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">{{ item.title }}</p>
                  <p class="text-xs text-muted-foreground mt-0.5 line-clamp-1">{{ item.description }}</p>
                </div>
              </div>
              <ArrowRight class="h-4 w-4 text-muted-foreground opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 group-hover:text-primary transition-all duration-300" />
            </router-link>
          </div>
        </div>

        <!-- Senado Federal -->
        <div class="bg-card rounded-lg border border-border p-6 shadow-sm relative">
          <div class="flex items-center gap-3 mb-6">
            <div class="p-2 rounded-md bg-purple-500/10">
              <Landmark class="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 class="text-xl font-bold text-foreground">Senado Federal</h3>
          
            </div>
          </div>
          
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <router-link
              v-for="item in senadoItems"
              :key="item.href"
              :to="item.href"
              class="group flex items-center justify-between p-4 rounded-lg bg-muted/50 hover:bg-muted border border-border/50 hover:border-purple-500/20 transition-all duration-200"
            >
              <div class="flex items-center gap-4">
                <div class="p-2 rounded-md bg-background text-muted-foreground group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                  <component :is="item.icon" class="h-5 w-5" />
                </div>
                <div>
                  <p class="text-sm font-semibold text-foreground group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">{{ item.title }}</p>
                  <p class="text-xs text-muted-foreground mt-0.5 line-clamp-1">{{ item.description }}</p>
                </div>
              </div>
              <ArrowRight class="h-4 w-4 text-muted-foreground opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-all duration-300" />
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { 
  Users, 
  Receipt, 
  Landmark, 
  Building2, 
  ArrowRight, 
  FileText, 
  GitCompare, 
  Store 
} from 'lucide-vue-next'
import { useSenadoStore } from '@/stores/senado'

const senadoresStore = useSenadoStore()
onMounted(() => {
  senadoresStore.fetchEstatisticasGerais()
  senadoresStore.fetchEstatisticasSenadores()
})

const camaraItems = [
  {
    title: "Deputados",
    description: "Perfis e atuação parlamentar",
    icon: Users,
    href: "/camara/deputados",
  },
  {
    title: "Despesas",
    description: "Gastos da cota parlamentar",
    icon: Receipt,
    href: "/camara/despesas",
  },
  {
    title: "Emendas",
    description: "Verbas destinadas pelos deputados",
    icon: Landmark,
    href: "/camara/emendas",
  },
  {
    title: "Projetos",
    description: "Projetos de lei e proposições",
    icon: FileText,
    href: "/camara/projetos-legislativos",
  },
  {
    title: "Comparar",
    description: "Compare atuação entre parlamentares",
    icon: GitCompare,
    href: "/camara/comparar",
  },
  {
    title: "Empresas",
    description: "Maiores fornecedores e recebedores",
    icon: Store,
    href: "/camara/empresas",
  },
]

const senadoItems = [
  {
    title: "Senadores",
    description: "Perfis e atuação no Senado",
    icon: Users,
    href: "/senado/senadores",
  },
  {
    title: "Despesas",
    description: "Gastos e reembolsos do Senado",
    icon: Receipt,
    href: "/senado/despesas",
  },
  {
    title: "Emendas",
    description: "Emendas dos senadores",
    icon: Landmark,
    href: "/senado/emendas",
  },
  {
    title: "Projetos",
    description: "Matérias e projetos legislativos",
    icon: FileText,
    href: "/senado/projetos-legislativos",
  },
  {
    title: "Comparar",
    description: "Análise comparativa de senadores",
    icon: GitCompare,
    href: "/senado/comparar",
  },
  {
    title: "Empresas",
    description: "Fornecedores e gastos do Senado",
    icon: Store,
    href: "/senado/empresas",
  },
]
</script>
