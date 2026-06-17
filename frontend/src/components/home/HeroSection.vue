<template>
  <section class="relative overflow-hidden bg-background border-b border-border/50">
    <!-- Background pattern -->
    <div class="absolute inset-0 opacity-5">
      <div class="absolute inset-0" :style="backgroundStyle" />
    </div>

    <div class="relative mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8 lg:py-32">
      <div class="grid lg:grid-cols-2 gap-12 items-center">
        <!-- Text content -->
        <div class="animate-fade-in-up">
          <div class="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary mb-6">
            <Eye class="h-4 w-4" />
            Transparência Legislativa
          </div>

          <h1 class="text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            Fiscaliza
            <span class="text-primary relative">
              Brasil
              <svg class="absolute -bottom-2 left-0 w-full h-3 text-secondary" viewBox="0 0 200 12">
                <path d="M0 8 Q 50 0, 100 8 T 200 8" stroke="currentColor" stroke-width="4" fill="none" />
              </svg>
            </span>
          </h1>

          <p class="mt-6 text-lg text-muted-foreground max-w-xl leading-relaxed">
            Fiscalize a atuação dos <strong>Deputados</strong> e <strong>Senadores</strong>. 
            Acompanhe gastos, emendas parlamentares e a representação política do Brasil de forma 
            transparente e acessível.
          </p>

          <div class="mt-8 flex flex-col sm:flex-row gap-4">
            <BaseButton to="/camara/deputados" size="lg" class="group">
              <Building2 class="mr-2 h-4 w-4" />
              Câmara dos Deputados
              <ArrowRight class="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </BaseButton>
            <BaseButton to="/senado/senadores" variant="outline" size="lg" class="group border-purple-500/50 hover:bg-purple-500/10">
              <Landmark class="mr-2 h-4 w-4 text-purple-500" />
              Senado Federal
              <ArrowRight class="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </BaseButton>
          </div>

          <div class="mt-10 flex items-center gap-6 text-sm text-muted-foreground">
            <div class="flex items-center gap-2">
              <div class="h-2 w-2 rounded-full bg-accent animate-pulse" />
              Dados públicos
            </div>
            <div class="flex items-center gap-2">
              <div class="h-2 w-2 rounded-full bg-primary animate-pulse" />
              100% transparente
            </div>
          </div>
        </div>

        <!-- Image/Visual -->
        <div class="relative animate-fade-in-up animate-delay-200">
          <div class="relative aspect-[4/3] rounded-2xl overflow-hidden shadow-2xl">
            <img
              src="/imagem-padrao.jpg"
              alt="Congresso Nacional do Brasil"
              class="object-cover w-full h-full"
            />
            <div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
            <div class="absolute bottom-4 left-4 right-4">
              <p class="text-white text-sm font-medium">Congresso Nacional, Brasília - DF</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Eye, ArrowRight, Building2, Landmark } from 'lucide-vue-next'
import BaseButton from '@/components/ui/BaseButton.vue'

const backgroundStyle = computed(() => ({
  backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fillRule=\'evenodd\'%3E%3Cg fill=\'%23228B22\' fillOpacity=\'0.4\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")'
}))
</script>
