<script setup lang="ts">
/**
 * Login View
 * 
 * Features:
 * - Username/password form
 * - Form validation
 * - Error display
 * - Link to register
 */

import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// Form state
const username = ref('')
const password = ref('')
const showPassword = ref(false)

// Validation
const usernameError = computed(() => {
  if (!username.value) return ''
  if (username.value.length < 3) return 'Username must be at least 3 characters'
  return ''
})

const passwordError = computed(() => {
  if (!password.value) return ''
  if (password.value.length < 6) return 'Password must be at least 6 characters'
  return ''
})

const isValid = computed(() => {
  return username.value.length >= 3 && password.value.length >= 6
})

// Handle submit
const handleSubmit = async () => {
  if (!isValid.value) return
  
  authStore.clearError()
  const success = await authStore.login({
    username: username.value,
    password: password.value
  })
  
  if (success) {
    const redirect = route.query.redirect as string || '/'
    router.push(redirect)
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
    <div class="w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-2xl mb-4">
          <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Welcome Back</h1>
        <p class="text-gray-600 dark:text-gray-400 mt-2">Sign in to your Knowledge Base</p>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
        <!-- Error alert -->
        <div v-if="authStore.error" class="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p class="text-sm text-red-600 dark:text-red-400">{{ authStore.error }}</p>
        </div>

        <!-- Username -->
        <div class="mb-5">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Username
          </label>
          <input
            v-model="username"
            type="text"
            autocomplete="username"
            class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors"
            placeholder="Enter your username"
          />
          <p v-if="usernameError" class="mt-1 text-sm text-red-500">{{ usernameError }}</p>
        </div>

        <!-- Password -->
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Password
          </label>
          <div class="relative">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password"
              class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors pr-12"
              placeholder="Enter your password"
            />
            <button
              type="button"
              @click="showPassword = !showPassword"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <svg v-if="showPassword" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
              </svg>
              <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
              </svg>
            </button>
          </div>
          <p v-if="passwordError" class="mt-1 text-sm text-red-500">{{ passwordError }}</p>
        </div>

        <!-- Submit -->
        <button
          type="submit"
          :disabled="!isValid || authStore.loading"
          class="w-full py-3 px-4 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center"
        >
          <svg v-if="authStore.loading" class="animate-spin -ml-1 mr-2 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ authStore.loading ? 'Signing in...' : 'Sign In' }}
        </button>

        <!-- Register link -->
        <p class="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
          Don't have an account?
          <router-link to="/register" class="text-primary-600 dark:text-primary-400 font-medium hover:underline">
            Create one
          </router-link>
        </p>
      </form>
    </div>
  </div>
</template>
