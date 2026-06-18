<template>
  <div class="min-h-screen flex flex-col">
    <main class="flex-1">
      <!-- Breadcrumb Skeleton -->
      <div class="bg-muted/30 border-b border-border">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <BaseSkeleton width="140px" height="20px" />
          <BaseSkeleton width="200px" height="32px" class="rounded-full" />
        </div>
      </div>

      <!-- Profile Section Skeleton -->
      <section class="py-8 bg-background border-b border-border/50">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div class="flex flex-col lg:flex-row gap-8">
            <!-- Profile Card Skeleton -->
            <div class="lg:w-80 flex-shrink-0">
              <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
                <div class="text-center space-y-4">
                  <!-- Avatar -->
                  <div class="flex justify-center">
                    <BaseSkeleton variant="circle" width="128px" height="128px" class="border-4 border-primary/10" />
                  </div>
                  <!-- Name -->
                  <div class="space-y-2 flex flex-col items-center">
                    <BaseSkeleton width="180px" height="24px" />
                    <div class="flex gap-2">
                      <BaseSkeleton width="100px" height="22px" class="rounded-full" />
                      <BaseSkeleton width="80px" height="22px" class="rounded-full" />
                    </div>
                  </div>
                  <!-- Info lines -->
                  <div class="space-y-4 pt-4">
                    <div v-for="i in 3" :key="i" class="flex items-center gap-2">
                      <BaseSkeleton variant="circle" width="16px" height="16px" />
                      <BaseSkeleton :width="['140px', '120px', '100px'][i-1]" height="16px" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Stats Cards Skeleton -->
            <div class="flex-1 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div v-for="i in 2" :key="i" class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
                <BaseSkeleton width="120px" height="14px" class="mb-3" />
                <BaseSkeleton width="100px" height="32px" class="mb-2" />
                <BaseSkeleton width="160px" height="12px" />
              </div>
              <!-- Full width card -->
              <div class="sm:col-span-2 lg:col-span-3 rounded-xl border bg-card text-card-foreground shadow-sm p-6">
                <BaseSkeleton width="200px" height="18px" class="mb-6" />
                <div class="space-y-4">
                  <div v-for="i in 4" :key="i" class="space-y-2">
                    <div class="flex justify-between">
                      <BaseSkeleton :width="[120, 160, 100, 140][i-1] + 'px'" height="14px" />
                      <BaseSkeleton width="80px" height="14px" />
                    </div>
                    <BaseSkeleton variant="rect" height="8px" class="rounded-full" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Emendas Table Skeleton -->
      <section class="py-8 bg-muted/20">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <BaseSkeleton width="180px" height="24px" class="mb-4" />
          <div class="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden">
            <div class="p-6 space-y-4">
              <!-- Table header -->
              <div class="flex gap-4 pb-3 border-b">
                <BaseSkeleton width="100px" height="14px" />
                <BaseSkeleton width="120px" height="14px" />
                <BaseSkeleton width="100px" height="14px" />
                <BaseSkeleton width="80px" height="14px" class="ml-auto" />
              </div>
              <!-- Table rows -->
              <div v-for="i in 3" :key="i" class="flex gap-4 py-2">
                <BaseSkeleton width="100px" height="14px" />
                <BaseSkeleton width="120px" height="14px" />
                <BaseSkeleton width="100px" height="14px" />
                <BaseSkeleton width="80px" height="14px" class="ml-auto" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Despesas Table Skeleton -->
      <section class="py-8">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <BaseSkeleton width="180px" height="24px" class="mb-4" />
          <div class="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden">
            <div class="p-6 space-y-4">
              <!-- Table header -->
              <div class="flex gap-4 pb-3 border-b">
                <BaseSkeleton width="80px" height="14px" />
                <BaseSkeleton width="200px" height="14px" />
                <BaseSkeleton width="80px" height="14px" class="ml-auto" />
                <BaseSkeleton width="40px" height="14px" />
              </div>
              <!-- Table rows -->
              <div v-for="i in 4" :key="i" class="flex gap-4 py-2">
                <BaseSkeleton width="80px" height="14px" />
                <BaseSkeleton width="200px" height="14px" />
                <BaseSkeleton width="80px" height="14px" class="ml-auto" />
                <BaseSkeleton width="40px" height="14px" />
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
</script>
