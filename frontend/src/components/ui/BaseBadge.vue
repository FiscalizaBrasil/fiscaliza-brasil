<template>
  <span
    class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-all duration-200"
    :class="variantClasses"
  >
    <slot />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  variant?: 'default' | 'outline' | 'secondary' | 'destructive' | 'success' | 'warning'
}>(), {
  variant: 'default'
})

const variantClasses = computed(() => {
  switch (props.variant) {
    case 'outline':
      return 'border border-border bg-transparent text-foreground'
    case 'secondary':
      return 'bg-secondary text-secondary-foreground border-secondary-foreground/20'
    case 'destructive':
      return 'bg-red-500/10 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-900/50'
    case 'success':
      return 'bg-green-500/10 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-900/50'
    case 'warning':
      return 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border border-yellow-200 dark:border-yellow-900/50'
    default:
      return 'bg-primary text-primary-foreground'
  }
})
</script>
