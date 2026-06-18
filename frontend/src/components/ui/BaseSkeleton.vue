<template>
  <div
    :class="[
      'animate-shimmer bg-gradient-to-r from-neutral-200 via-neutral-100 to-neutral-200 bg-[length:200%_100%]',
      variant === 'circle' ? 'rounded-full' : 'rounded-md',
      variant === 'text' ? 'h-4 w-full' : '',
      className
    ]"
    :style="customStyle"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  variant?: 'text' | 'circle' | 'rect' | 'card'
  width?: string
  height?: string
  className?: string
}>(), {
  variant: 'text',
  className: ''
})

const customStyle = computed(() => {
  const style: Record<string, string> = {}
  if (props.width) style.width = props.width
  if (props.height) style.height = props.height
  if (props.variant === 'circle') {
    style.width = props.width || '48px'
    style.height = props.height || props.width || '48px'
  }
  if (props.variant === 'card') {
    style.height = props.height || '120px'
  }
  return style
})
</script>

<style scoped>
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.animate-shimmer {
  animation: shimmer 1.8s ease-in-out infinite;
}
</style>
