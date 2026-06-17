<template>
  <div :class="['flex flex-col items-center justify-center py-12', fullPage ? 'absolute inset-0 bg-background/80 backdrop-blur-sm z-[100]' : '']">
    <div class="relative">
      <!-- Outer spinning ring -->
      <div 
        class="h-12 w-12 rounded-full border-4 border-primary/20 border-t-primary animate-spin"
      ></div>
      <!-- Inner pulsing circle -->
      <div 
        class="absolute inset-0 h-10 w-10 m-auto rounded-full bg-primary/10 animate-pulse"
      ></div>
    </div>
    <p v-if="message" class="mt-4 text-sm font-medium text-muted-foreground animate-pulse">
      {{ message }}
    </p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  message?: string
  fullPage?: boolean
}>()
</script>

<style scoped>
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
