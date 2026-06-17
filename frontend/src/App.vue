<template>
  <div class="min-h-screen flex flex-col relative w-full h-full text-foreground bg-background">
    <AppHeader />
    
    <main class="flex-1 relative flex flex-col z-0">
      <!-- Loading Overlay -->
      <transition name="fade">
        <div 
          v-if="(isRouteLoading || loadingStore.isLoading) && $route.name !== 'home'" 
          class="absolute inset-0 z-[100] flex items-center justify-center bg-background/70 backdrop-blur-sm"
        >
          <BaseLoading :message="loadingStore.message || 'Carregando...'" />
        </div>
      </transition>

      <!-- Content -->
      <router-view />
    </main>

    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useLoadingStore } from '@/stores/loading'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import BaseLoading from '@/components/ui/BaseLoading.vue'

const router = useRouter()
const loadingStore = useLoadingStore()
const isRouteLoading = ref(false)

router.beforeEach((to, from, next) => {
  if (to.name !== from.name) {
    isRouteLoading.value = true
  }
  next()
})

router.afterEach(() => {
  // Add a small delay for visual feedback
  setTimeout(() => {
    isRouteLoading.value = false
  }, 300)
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
