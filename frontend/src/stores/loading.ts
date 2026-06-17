import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useLoadingStore = defineStore('loading', () => {
  const isLoading = ref(false)
  const message = ref('')

  const startLoading = (msg = 'Carregando...') => {
    isLoading.value = true
    message.value = msg
  }

  const stopLoading = () => {
    isLoading.value = false
    message.value = ''
  }

  return {
    isLoading,
    message,
    startLoading,
    stopLoading
  }
})
