<template>
  <footer class="border-t border-border bg-muted/30">
    <div class="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <div class="grid grid-cols-1 gap-8 md:grid-cols-4">
        <!-- About -->
        <div class="md:col-span-2">
          <div class="flex items-center gap-2 mb-4">
            <div class="flex h-10 w-10 items-center justify-center">
              <img src="/logo.svg" alt="Logo" class="h-10 w-10 object-contain" />
            </div>
            <span class="font-bold text-lg text-foreground">Fiscaliza Brasil</span>
          </div>
          <p class="text-sm text-muted-foreground max-w-md">
            Plataforma de transparência política dedicada a monitorar a atuação dos deputados e senadores brasileiros.
            Fiscalize gastos, emendas e acompanhe a representação política do Brasil.
          </p>
        </div>

        <!-- Data Sources -->
        <div>
          <h3 class="text-sm font-semibold text-foreground mb-4">Fontes de Dados</h3>
          <ul class="space-y-3">
            <li v-for="source in dataSources" :key="source.url">
              <a
                :href="source.url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-sm text-muted-foreground hover:text-primary transition-colors"
              >
                {{ source.name }}
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div class="mt-8 pt-8 border-t border-border flex flex-col sm:flex-row justify-between items-center gap-4">
        <p class="text-xs text-muted-foreground">
          © 2026 Fiscaliza Brasil. Dados públicos para uma democracia transparente.
        </p>
        <div class="flex gap-4">
          <!-- contato removido -->
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">

const dataSources = [
  { name: 'Dados Abertos da Câmara', url: 'https://dadosabertos.camara.leg.br' },
  { name: 'Dados Abertos do Senado', url: 'https://www12.senado.leg.br/dados-abertos' },
  { name: 'Portal da Transparência', url: 'https://portaldatransparencia.gov.br' },
]
</script>
