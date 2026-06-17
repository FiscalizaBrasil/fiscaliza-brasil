<template>
  <span>{{ prefix }}{{ formattedValue }}{{ suffix }}</span>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'

const props = withDefaults(defineProps<{
  value: number
  prefix?: string
  suffix?: string
}>(), {
  prefix: '',
  suffix: ''
})

const displayValue = ref(0)

const formattedValue = computed(() => {
  if (props.value >= 1000) {
    return displayValue.value.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
  }
  return displayValue.value.toFixed(props.value < 10 ? 1 : 0)
})

onMounted(() => {
  const duration = 2000
  const steps = 60
  const stepValue = props.value / steps
  let current = 0

  const timer = setInterval(() => {
    current += stepValue
    if (current >= props.value) {
      displayValue.value = props.value
      clearInterval(timer)
    } else {
      displayValue.value = current
    }
  }, duration / steps)
})
</script>
