<script setup lang="ts">
/**
 * App.vue - Main Layout
 * 
 * Layout:
 * - Navbar (top): Navigation links + Dark/Light toggle
 * - Sidebar (left): Chat history
 * - Main content area: Router view
 */

import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore, useThemeStore } from '@/stores'
import Navbar from '@/components/Navbar.vue'
import Sidebar from '@/components/Sidebar.vue'

const route = useRoute()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const sidebarOpen = ref(true)
const initialized = ref(false)

// Check if current route is auth page (login/register)
const isAuthPage = () => {
  return route.name === 'Login' || route.name === 'Register'
}

// Toggle sidebar
const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

// Initialize app
onMounted(async () => {
  // Apply initial theme
  themeStore.setTheme(themeStore.theme)
  
  // Try to fetch user if token exists
  await authStore.fetchUser()
  initialized.value = true
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
    <!-- Loading state -->
    <div v-if="!initialized" class="flex items-center justify-center min-h-screen">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
    </div>

    <!-- Auth pages (no navbar/sidebar) -->
    <template v-else-if="isAuthPage()">
      <router-view />
    </template>

    <!-- Main app layout -->
    <template v-else>
      <!-- Navbar -->
      <Navbar @toggle-sidebar="toggleSidebar" />

      <div class="flex pt-16">
        <!-- Sidebar -->
        <transition name="slide">
          <Sidebar v-if="sidebarOpen && authStore.isAuthenticated" />
        </transition>

        <!-- Main content -->
        <main 
          class="flex-1 transition-all duration-300"
          :class="{ 'ml-64': sidebarOpen && authStore.isAuthenticated }"
        >
          <div class="p-6">
            <router-view />
          </div>
        </main>
      </div>
    </template>
  </div>
</template>
