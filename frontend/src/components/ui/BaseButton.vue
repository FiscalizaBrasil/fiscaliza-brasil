<template>
  <component
    :is="to ? 'router-link' : 'button'"
    :to="to"
    :type="to ? undefined : type"
    :disabled="disabled"
    class="inline-flex items-center justify-center rounded-md font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]"
    :class="[variantClasses, sizeClasses]"
  >
    <slot />
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  variant?: 'default' | 'outline' | 'ghost' | 'secondary'
  size?: 'sm' | 'md' | 'lg' | 'icon'
  to?: string
  type?: 'button' | 'submit'
  disabled?: boolean
}>(), {
  variant: 'default',
  size: 'md',
  type: 'button'
})

const variantClasses = computed(() => {
  switch (props.variant) {
    case 'outline':
      return 'border border-border bg-transparent hover:bg-muted hover:border-primary/30'
    case 'ghost':
      return 'hover:bg-muted'
    case 'secondary':
      return 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
    default:
      return 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm hover:shadow-md'
  }
})

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'h-8 px-3 text-sm'
    case 'lg':
      return 'h-12 px-6 text-base'
    case 'icon':
      return 'h-10 w-10'
    default:
      return 'h-10 px-4 text-sm'
  }
})
</script>
