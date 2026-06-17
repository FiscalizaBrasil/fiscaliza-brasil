<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <HeroSection />
      <StatsSection />

      <FeaturesSection />

    </main>
  </div>
</template>

<script setup lang="ts">
import HeroSection from '@/components/home/HeroSection.vue'
import StatsSection from '@/components/home/StatsSection.vue'

import FeaturesSection from '@/components/home/FeaturesSection.vue'

</script>
