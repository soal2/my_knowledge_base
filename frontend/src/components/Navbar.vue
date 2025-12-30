<script setup lang="ts">
/**
 * Navbar Component
 * 
 * Features:
 * - Navigation links: Chat, Files, Profile
 * - Dark/Light mode toggle
 * - User menu with logout
 */

import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore, useThemeStore } from '@/stores'

const emit = defineEmits<{
  'toggle-sidebar': []
}>()

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const navLinks = [
  { name: 'Chat', path: '/', icon: 'chat' },
  { name: 'Knowledge Base', path: '/files', icon: 'folder' },
  { name: 'Profile', path: '/profile', icon: 'user' }
]

const isActive = (path: string) => {
  return route.path === path
}

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}

const isDark = computed(() => themeStore.theme === 'dark')
</script>

<template>
  <nav class="fixed top-0 left-0 right-0 h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 z-50">
    <div class="h-full px-4 flex items-center justify-between">
      <!-- Left: Toggle + Logo -->
      <div class="flex items-center gap-4">
        <!-- Sidebar toggle -->
        <button
          @click="emit('toggle-sidebar')"
          class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          title="Toggle Sidebar"
        >
          <svg class="w-6 h-6 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </button>

        <!-- Logo -->
        <router-link to="/" class="flex items-center gap-2">
          <div class="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
            </svg>
          </div>
          <span class="text-lg font-semibold text-gray-800 dark:text-white hidden sm:block">
            Knowledge Base
          </span>
        </router-link>
      </div>

      <!-- Center: Navigation -->
      <div class="hidden md:flex items-center gap-1">
        <router-link
          v-for="link in navLinks"
          :key="link.path"
          :to="link.path"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="isActive(link.path) 
            ? 'bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300' 
            : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'"
        >
          {{ link.name }}
        </router-link>
      </div>

      <!-- Right: Theme toggle + User -->
      <div class="flex items-center gap-3">
        <!-- Theme toggle -->
        <button
          @click="themeStore.toggleTheme()"
          class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          :title="isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
        >
          <!-- Sun icon -->
          <svg v-if="isDark" class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.166a.75.75 0 00-1.06-1.06l-1.591 1.59a.75.75 0 101.06 1.061l1.591-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.834 18.894a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 10-1.061 1.06l1.59 1.591zM12 18a.75.75 0 01.75.75V21a.75.75 0 01-1.5 0v-2.25A.75.75 0 0112 18zM7.758 17.303a.75.75 0 00-1.061-1.06l-1.591 1.59a.75.75 0 001.06 1.061l1.591-1.59zM6 12a.75.75 0 01-.75.75H3a.75.75 0 010-1.5h2.25A.75.75 0 016 12zM6.697 7.757a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 00-1.061 1.06l1.59 1.591z"/>
          </svg>
          <!-- Moon icon -->
          <svg v-else class="w-5 h-5 text-gray-600" fill="currentColor" viewBox="0 0 24 24">
            <path fill-rule="evenodd" d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69.75.75 0 01.981.98 10.503 10.503 0 01-9.694 6.46c-5.799 0-10.5-4.701-10.5-10.5 0-4.368 2.667-8.112 6.46-9.694a.75.75 0 01.818.162z" clip-rule="evenodd"/>
          </svg>
        </button>

        <!-- User info -->
        <div v-if="authStore.isAuthenticated" class="flex items-center gap-3">
          <span class="text-sm text-gray-600 dark:text-gray-300 hidden sm:block">
            {{ authStore.username }}
          </span>
          <button
            @click="handleLogout"
            class="px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
          >
            Logout
          </button>
        </div>
      </div>
    </div>
  </nav>
</template>
