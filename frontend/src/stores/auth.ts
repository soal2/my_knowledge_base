/**
 * Auth Store
 * Manages user authentication state
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, getAccessToken, clearTokens } from '@/api'
import type { User, LoginCredentials, RegisterCredentials } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!user.value)
  const username = computed(() => user.value?.username || '')

  // Actions
  async function login(credentials: LoginCredentials): Promise<boolean> {
    loading.value = true
    error.value = null
    
    try {
      const response = await authApi.login(credentials)
      if (response.success) {
        user.value = response.data.user
        return true
      } else {
        error.value = response.message
        return false
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { message?: string } } }
      error.value = axiosError.response?.data?.message || 'Login failed'
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(credentials: RegisterCredentials): Promise<boolean> {
    loading.value = true
    error.value = null
    
    try {
      const response = await authApi.register(credentials)
      if (response.success) {
        user.value = response.data.user
        return true
      } else {
        error.value = response.message
        return false
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { message?: string } } }
      error.value = axiosError.response?.data?.message || 'Registration failed'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchUser(): Promise<boolean> {
    if (!getAccessToken()) {
      return false
    }
    
    loading.value = true
    
    try {
      const response = await authApi.me()
      if (response.success) {
        user.value = response.data
        return true
      }
      return false
    } catch {
      clearTokens()
      user.value = null
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } finally {
      user.value = null
      clearTokens()
    }
  }

  function clearError(): void {
    error.value = null
  }

  return {
    // State
    user,
    loading,
    error,
    // Getters
    isAuthenticated,
    username,
    // Actions
    login,
    register,
    fetchUser,
    logout,
    clearError
  }
})
