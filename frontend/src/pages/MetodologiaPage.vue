<template>
  <div class="min-h-screen flex flex-col bg-background">
    <main class="flex-1">
      <!-- Hero -->
      <section class="relative overflow-hidden bg-background border-b border-border/50 py-20 lg:py-28">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <span class="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary mb-6">
            <BookOpen class="h-4 w-4" />
            Guia &amp; Metodologia
          </span>
          <h1 class="text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            Entenda como <span class="text-primary">fiscalizamos</span>
          </h1>
          <p class="mt-6 text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Saiba de onde vêm os dados, como são processados e o que cada seção do Fiscaliza Brasil oferece para você acompanhar a atuação parlamentar.
          </p>
        </div>
      </section>

      <!-- Como funciona - 3 steps -->
      <section class="py-16 bg-muted/30">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="text-center mb-12">
            <h2 class="text-3xl font-bold text-foreground">Como funciona?</h2>
            <p class="mt-2 text-muted-foreground">Em 3 etapas simples</p>
          </div>

          <div class="grid gap-8 md:grid-cols-3">
            <div v-for="step in steps" :key="step.title" class="text-center">
              <h3 class="text-lg font-bold text-foreground">{{ step.title }}</h3>
              <p class="mt-2 text-sm text-muted-foreground leading-relaxed">{{ step.description }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Fontes de Dados -->
      <section class="py-16">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="text-center mb-12">
            <h2 class="text-3xl font-bold text-foreground">Entenda os Dados</h2>
            <p class="mt-2 text-muted-foreground">Informações sobre as fontes e tipos de dados exibidos</p>
          </div>

          <div class="flex flex-wrap justify-center gap-6">
            <div
              v-for="source in dataSources"
              :key="source.title"
              class="bg-card rounded-xl border border-border p-6 hover:shadow-lg transition-shadow w-full md:w-[calc(50%-12px)] lg:w-[calc(33.333%-16px)]"
            >
              <div class="flex items-center gap-3 mb-4">
                <div class="p-2.5 rounded-lg bg-primary/10">
                  <component :is="source.icon" class="h-5 w-5 text-primary" />
                </div>
                <h3 class="font-bold text-foreground">{{ source.title }}</h3>
              </div>
              <ul class="space-y-2">
                <li v-for="(item, idx) in source.items" :key="idx" class="flex items-start gap-2 text-sm text-muted-foreground">
                  <ChevronRight class="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>{{ item }}</span>
                </li>
              </ul>
              <p class="mt-4 text-xs text-muted-foreground/70 border-t border-border pt-3">
                Fonte: {{ source.fonte }}
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- O que você pode fazer -->
      <section class="py-16 bg-muted/30">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="text-center mb-12">
            <h2 class="text-3xl font-bold text-foreground">O que você pode fazer</h2>
            <p class="mt-2 text-muted-foreground max-w-xl mx-auto">Cada funcionalidade foi pensada para você entender o que acontece no Congresso</p>
          </div>

          <div class="space-y-12">
            <div
              v-for="(feature, idx) in features"
              :key="feature.title"
              class="grid lg:grid-cols-2 gap-8 items-center"
            >
              <!-- Texto -->
              <div :class="idx % 2 !== 0 ? 'lg:order-2' : ''">
                <div class="bg-card rounded-xl border border-border p-6 lg:p-8 hover:shadow-lg transition-shadow">
                  <h3 class="text-xl font-bold text-foreground mb-2">{{ feature.title }}</h3>
                  <p class="text-muted-foreground leading-relaxed mb-4">{{ feature.description }}</p>
                  <ul class="space-y-1.5 mb-4">
                    <li v-for="(tip, i) in feature.tips" :key="i" class="flex items-center gap-2 text-sm text-muted-foreground">
                      <Check class="h-4 w-4 text-primary flex-shrink-0" />
                      {{ tip }}
                    </li>
                  </ul>
                </div>
              </div>
              <!-- Visual -->
              <div :class="idx % 2 !== 0 ? 'lg:order-1' : ''">
                <div class="bg-muted/50 rounded-xl border border-border p-8 flex items-center justify-center h-full min-h-[200px]">
                  <component :is="feature.icon" class="h-16 w-16 text-primary/30" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- FAQ -->
      <section class="py-16 bg-muted/30">
        <div class="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <div class="text-center mb-12">
            <h2 class="text-3xl font-bold text-foreground">Perguntas Frequentes</h2>
            <p class="mt-2 text-muted-foreground">Tire suas dúvidas sobre a plataforma</p>
          </div>

          <div class="space-y-3">
            <div
              v-for="(faq, idx) in faqs"
              :key="idx"
              class="bg-card rounded-lg border border-border overflow-hidden"
            >
              <button
                class="w-full flex items-center justify-between p-5 text-left hover:bg-muted/50 transition-colors"
                @click="toggleFaq(idx)"
              >
                <span class="font-medium text-foreground pr-4">{{ faq.question }}</span>
                <ChevronDown
                  class="h-5 w-5 text-muted-foreground flex-shrink-0 transition-transform duration-200"
                  :class="{ 'rotate-180': openFaq === idx }"
                />
              </button>
              <div
                v-if="openFaq === idx"
                class="px-5 pb-5 text-sm text-muted-foreground leading-relaxed border-t border-border pt-4"
              >
                {{ faq.answer }}
              </div>
            </div>
          </div>
        </div>
      </section>

    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  BookOpen, Database, Receipt, FileText,
  Vote, ChevronRight, ChevronDown, Check, Scale, Users
} from 'lucide-vue-next'

// Steps
const steps = [
  { number: 1, title: 'Coletamos', description: 'Dados públicos oficiais da Câmara dos Deputados, Senado Federal e Portal da Transparência são integrados periodicamente à plataforma.' },
  { number: 2, title: 'Processamos', description: 'As informações são organizadas, categorizadas e armazenadas em nosso banco de dados para consulta rápida e análise.' },
  { number: 3, title: 'Você Fiscaliza', description: 'Navegue pelos dados, compare parlamentares, analise gastos e acompanhe votações de forma clara e acessível.' },
]

// Data sources
const dataSources = [
  {
    title: 'Cota Parlamentar',
    icon: Receipt,
    items: [
      'Sistema de reembolso de despesas dos parlamentares',
      'Categorias: passagens, alimentação, combustíveis, etc.',
    ],
    fonte: 'API da Câmara e do Senado',
  },
  {
    title: 'Emendas Parlamentares',
    icon: FileText,
    items: [
      'Emendas individuais e de bancada',
      'Classificadas por área e município beneficiado',
      'Valores pagos e classificação por função',
    ],
    fonte: 'Portal da Transparência e bases oficiais integradas',
  },
  {
    title: 'Votações',
    icon: Vote,
    items: [
      'Registro nominal de votos dos parlamentares',
      'Dados desde 2007 até a legislatura atual',
      'Resultado completo de cada votação',
    ],
    fonte: 'API da Câmara e do Senado',
  },
  {
    title: 'Projetos Legislativos',
    icon: FileText,
    items: [
      'Projetos de lei, PECs, medidas provisórias',
      'Autoria, tramitação e situação atual',
      'Filtros por tipo, ano e autor',
    ],
    fonte: 'API da Câmara e do Senado',
  },
  {
    title: 'Perfis Parlamentares',
    icon: Database,
    items: [
      'Dados biográficos e contato dos parlamentares',
      'Partido, estado, escolaridade e mandato',
      'Foto oficial e informações de gabinete',
    ],
    fonte: 'API da Câmara e do Senado',
  },
]

// Features
const features = [
  {
    title: 'Veja quem mais gasta',
    description: 'O painel de despesas mostra os parlamentares e partidos que mais utilizam a cota parlamentar, com rankings, totais e análises por categoria.',
    tips: ['Filtre por partido ou estado', 'Veja gastos por categoria', 'Câmara e Senado disponíveis'],
    icon: Receipt,
  },
  {
    title: 'Compare parlamentares lado a lado',
    description: 'Escolha dois parlamentares e compare perfis, gastos totais, categorias de despesas e últimas notas fiscais em uma única tela.',
    tips: ['Compare parlamentares do mesmo estado', 'Veja diferença percentual de gastos', 'Disponível para Câmara e Senado'],
    icon: Scale,
  },
  {
    title: 'Acompanhe as votações',
    description: 'Veja como cada parlamentar votou nos projetos legislativos. Descubra padrões de votação e alinhamento partidário.',
    tips: ['Veja o placar completo de cada votação', 'Filtre por projeto legislativo ou parlamentar', 'Dados desde 2007'],
    icon: Vote,
  },
  {
    title: 'Acompanhe emendas parlamentares',
    description: 'Descubra quais parlamentares mais destinaram emendas, para quais municípios e em quais áreas como saúde, educação e infraestrutura.',
    tips: ['Emendas individuais e de bancada', 'Valores pagos por parlamentar', 'Classificação por área'],
    icon: FileText,
  },
  {
    title: 'Conheça cada parlamentar a fundo',
    description: 'Clique em qualquer parlamentar para ver o perfil completo: histórico de gastos, despesas detalhadas, partido e informações pessoais.',
    tips: ['Veja a evolução dos gastos', 'Confira as últimas despesas', 'Acesse informações de contato'],
    icon: Users,
  },
]

// FAQ
const faqs = [
  {
    question: 'De onde vêm os dados?',
    answer: 'Os dados são obtidos de fontes oficiais, incluindo as bases da Câmara dos Deputados, do Senado Federal e do Portal da Transparência do Governo Federal. São dados públicos, disponíveis para qualquer cidadão.',
  },
  {
    question: 'O que é a Cota Parlamentar (CEAP)?',
    answer: 'A Cota para Exercício da Atividade Parlamentar (CEAP) é um valor mensal que cada deputado pode usar para custear despesas relacionadas ao mandato, como passagens aéreas, alimentação, combustível, telefonia e materiais de escritório. O valor varia por estado.',
  },
  {
    question: 'O que são emendas parlamentares?',
    answer: 'São instrumentos pelos quais os parlamentares podem destinar recursos do orçamento federal para obras e serviços em seus estados ou municípios. Podem ser individuais, de bancada ou de comissão.',
  },
  {
    question: 'Posso confiar nos dados apresentados?',
    answer: 'Sim. Utilizamos exclusivamente fontes oficiais do governo. O projeto é de código aberto e está disponível para auditoria pública. Não fazemos nenhuma alteração nos dados originais — apenas organizamos e apresentamos de forma mais acessível.',
  },
  {
    question: 'O Fiscaliza Brasil tem algum viés político?',
    answer: 'Não. A plataforma apresenta dados objetivos sem qualquer viés partidário ou ideológico. Os rankings e comparações são baseados exclusivamente em métricas numéricas dos dados oficiais.',
  },
]

const openFaq = ref<number | null>(null)
const toggleFaq = (idx: number) => {
  openFaq.value = openFaq.value === idx ? null : idx
}
</script>
