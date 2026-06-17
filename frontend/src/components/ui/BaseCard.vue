<template>
  <div
    :class="[
      variantClass,
      hover && 'hover:shadow-lg hover:-translate-y-1 hover:border-primary/30',
      clickable && 'cursor-pointer'
    ]"
  >
    <div v-if="$slots.header" class="flex flex-col space-y-1.5 p-6">
      <slot name="header" />
    </div>
    <div class="p-6" :class="{ 'pt-0': $slots.header }">
      <slot />
    </div>
    <div v-if="$slots.footer" class="flex items-center p-6 pt-0">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  hover?: boolean
  clickable?: boolean
  variant?: 'default' | 'kpi' | 'flat' | 'elevated'
}>(), {
  variant: 'default'
})

const variantClass = computed(() => {
  switch (props.variant) {
    case 'kpi':
      return 'card-kpi'
    case 'flat':
      return 'card-flat'
    case 'elevated':
      return 'card-elevated'
    default:
      return 'card-default'
  }
})
</script>
