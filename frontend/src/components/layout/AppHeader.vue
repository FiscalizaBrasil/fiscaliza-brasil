<template>
  <header class="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
    <nav class="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 lg:px-8">
      <div class="flex lg:flex-1">
        <router-link to="/" class="flex items-center gap-2">
          <img src="/logo.svg" alt="Logo" class="h-8 w-8 sm:h-10 sm:w-10 object-contain" />
          <span class="font-bold text-base sm:text-lg text-foreground">Fiscaliza Brasil</span>
        </router-link>
      </div>

      <!-- Mobile menu button -->
      <div class="flex lg:hidden">
        <button
          type="button"
          class="-m-2.5 inline-flex items-center justify-center rounded-md p-2.5 text-foreground"
          @click="mobileMenuOpen = true"
        >
          <span class="sr-only">Abrir menu</span>
          <Menu class="h-6 w-6" />
        </button>
      </div>

      <!-- Desktop nav -->
      <div class="hidden lg:flex lg:gap-x-6">
        <router-link
          to="/"
          class="text-sm font-semibold leading-6 transition-colors hover:text-primary"
          :class="$route.path === '/' ? 'text-primary' : 'text-muted-foreground'"
        >
          Home
        </router-link>

        <!-- Câmara Dropdown -->
        <div class="relative group">
          <button
            class="text-sm font-semibold leading-6 transition-colors hover:text-primary inline-flex items-center gap-1"
            :class="$route.path.startsWith('/camara') ? 'text-primary' : 'text-muted-foreground'"
          >
            Câmara
            <ChevronDown class="h-4 w-4" />
          </button>
          <div class="absolute left-0 top-full pt-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
            <div class="bg-background border border-border rounded-lg shadow-lg py-2 min-w-[160px]">
              <router-link
                v-for="item in camaraItems"
                :key="item.href"
                :to="item.href"
                class="block px-4 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                {{ item.name }}
              </router-link>
            </div>
          </div>
        </div>

        <!-- Senado Dropdown -->
        <div class="relative group">
          <button
            class="text-sm font-semibold leading-6 transition-colors hover:text-primary inline-flex items-center gap-1"
            :class="$route.path.startsWith('/senado') ? 'text-primary' : 'text-muted-foreground'"
          >
            Senado
            <ChevronDown class="h-4 w-4" />
          </button>
          <div class="absolute left-0 top-full pt-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
            <div class="bg-background border border-border rounded-lg shadow-lg py-2 min-w-[160px]">
              <router-link
                v-for="item in senadoItems"
                :key="item.href"
                :to="item.href"
                class="block px-4 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                {{ item.name }}
              </router-link>
            </div>
          </div>
        </div>
        
        <!-- Metodologia -->
        <router-link
          to="/metodologia"
          class="text-sm font-semibold leading-6 transition-colors hover:text-primary"
          :class="$route.path === '/metodologia' ? 'text-primary' : 'text-muted-foreground'"
        >
          Metodologia
        </router-link>

      </div>

      <div class="hidden lg:flex lg:flex-1 lg:justify-end lg:gap-x-4">
      </div>
    </nav>
  </header>

  <!-- Mobile menu - Teleported to body to avoid backdrop-filter breaking fixed positioning -->
  <Teleport to="body">
    <Transition name="overlay">
      <div
        v-if="mobileMenuOpen"
        class="fixed inset-0 bg-black/50 z-[100] lg:hidden"
        @click="mobileMenuOpen = false"
      />
    </Transition>
    <Transition name="drawer">
      <div
        v-if="mobileMenuOpen"
        class="fixed inset-y-0 right-0 w-full max-w-sm bg-background px-6 py-6 overflow-y-auto z-[101] shadow-xl lg:hidden"
      >
        <div class="flex items-center justify-between">
          <router-link to="/" class="flex items-center gap-2" @click="mobileMenuOpen = false">
            <img src="/logo.svg" alt="Logo" class="h-8 w-8 object-contain" />
            <span class="font-bold text-base text-foreground">Fiscaliza Brasil</span>
          </router-link>
          <button type="button" class="-m-2.5 rounded-md p-2.5 text-foreground" @click="mobileMenuOpen = false">
            <X class="h-6 w-6" />
          </button>
        </div>
        <div class="mt-6 flow-root">
          <div class="-my-6 divide-y divide-border">
            <div class="space-y-2 py-6">
              <router-link
                to="/"
                class="-mx-3 block rounded-lg px-3 py-2 text-base font-semibold leading-7 transition-colors hover:bg-muted"
                :class="$route.path === '/' ? 'text-primary bg-muted' : 'text-foreground'"
                @click="mobileMenuOpen = false"
              >
                Home
              </router-link>

              <!-- Câmara Section -->
              <div class="pt-2">
                <p class="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Câmara</p>
                <router-link
                  v-for="item in camaraItems"
                  :key="item.href"
                  :to="item.href"
                  class="-mx-3 block rounded-lg px-3 py-2 text-base font-semibold leading-7 transition-colors hover:bg-muted"
                  :class="$route.path === item.href ? 'text-primary bg-muted' : 'text-foreground'"
                  @click="mobileMenuOpen = false"
                >
                  {{ item.name }}
                </router-link>
              </div>

              <!-- Senado Section -->
              <div class="pt-2">
                <p class="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Senado</p>
                <router-link
                  v-for="item in senadoItems"
                  :key="item.href"
                  :to="item.href"
                  class="-mx-3 block rounded-lg px-3 py-2 text-base font-semibold leading-7 transition-colors hover:bg-muted"
                  :class="$route.path === item.href ? 'text-primary bg-muted' : 'text-foreground'"
                  @click="mobileMenuOpen = false"
                >
                  {{ item.name }}
                </router-link>
              </div>

              <!-- Metodologia Section -->
              <div class="pt-2">
                <router-link
                  to="/metodologia"
                  class="-mx-3 block rounded-lg px-3 py-2 text-base font-semibold leading-7 transition-colors hover:bg-muted"
                  :class="$route.path === '/metodologia' ? 'text-primary bg-muted' : 'text-foreground'"
                  @click="mobileMenuOpen = false"
                >
                  Metodologia
                </router-link>
              </div>

            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Menu, X, ChevronDown } from 'lucide-vue-next'

const camaraItems = [
  { name: 'Deputados', href: '/camara/deputados' },
  { name: 'Comparar Deputados', href: '/camara/comparar' },
  { name: 'Projetos Legislativos', href: '/camara/projetos-legislativos' },
  { name: 'Despesas', href: '/camara/despesas' },
  { name: 'Emendas', href: '/camara/emendas' },
  { name: 'Empresas', href: '/camara/empresas' },
]

const senadoItems = [
  { name: 'Senadores', href: '/senado/senadores' },
  { name: 'Comparar Senadores', href: '/senado/comparar' },
  { name: 'Projetos Legislativos', href: '/senado/projetos-legislativos' },
  { name: 'Despesas', href: '/senado/despesas' },
  { name: 'Emendas', href: '/senado/emendas' },
  { name: 'Empresas', href: '/senado/empresas' },
]

const mobileMenuOpen = ref(false)

// Lock body scroll when mobile menu is open
watch(mobileMenuOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})
</script>

<style scoped>
/* Overlay fade */
.overlay-enter-active,
.overlay-leave-active {
  transition: opacity 0.25s ease;
}
.overlay-enter-from,
.overlay-leave-to {
  opacity: 0;
}

/* Drawer slide */
.drawer-enter-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-leave-active {
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(100%);
}
</style>
