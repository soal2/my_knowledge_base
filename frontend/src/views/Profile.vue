<script setup lang="ts">
/**
 * Profile View
 * 
 * Features:
 * - API Keys management (Qwen, DeepSeek)
 * - User stats display
 * - Password change
 */

import { ref, computed, onMounted } from 'vue'
import { settingsApi } from '@/api'
import { useAuthStore } from '@/stores'
import type { APIKey, Provider } from '@/types'

const authStore = useAuthStore()

// State
const apiKeys = ref<APIKey[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// Form state
const newKey = ref({
  provider: 'qwen' as Provider,
  api_key: ''
})

// Stats
const stats = ref({
  documents: { total: 0, completed: 0 },
  chat: { sessions: 0, messages: 0 },
  api_keys: 0
})

// Providers list
const providers: { value: Provider; label: string; description: string }[] = [
  { value: 'qwen', label: 'Qwen (通义千问)', description: 'DashScope API' },
  { value: 'deepseek', label: 'DeepSeek', description: 'OpenAI-compatible API' },
  { value: 'openai', label: 'OpenAI', description: 'GPT-4, GPT-3.5' },
  { value: 'anthropic', label: 'Anthropic', description: 'Claude models' }
]

// Get key for provider
const getKeyForProvider = (provider: Provider): APIKey | undefined => {
  return apiKeys.value.find(k => k.provider === provider)
}

// Fetch API keys
const fetchKeys = async () => {
  loading.value = true
  try {
    const response = await settingsApi.getKeys()
    if (response.success) {
      apiKeys.value = response.data
    }
  } catch (err) {
    console.error('Failed to fetch API keys:', err)
  } finally {
    loading.value = false
  }
}

// Fetch stats
const fetchStats = async () => {
  try {
    const response = await settingsApi.getStats()
    if (response.success) {
      stats.value = response.data
    }
  } catch (err) {
    console.error('Failed to fetch stats:', err)
  }
}

// Save API key
const handleSaveKey = async () => {
  if (!newKey.value.api_key.trim()) {
    error.value = 'API key is required'
    return
  }
  
  saving.value = true
  error.value = null
  successMessage.value = null
  
  try {
    const response = await settingsApi.saveKey({
      provider: newKey.value.provider,
      api_key: newKey.value.api_key
    })
    
    if (response.success) {
      successMessage.value = `API key for ${newKey.value.provider} saved successfully`
      newKey.value.api_key = ''
      await fetchKeys()
    }
  } catch (err: unknown) {
    const axiosError = err as { response?: { data?: { message?: string } } }
    error.value = axiosError.response?.data?.message || 'Failed to save API key'
  } finally {
    saving.value = false
  }
}

// Delete API key
const handleDeleteKey = async (provider: Provider) => {
  if (!confirm(`Are you sure you want to delete the ${provider} API key?`)) return
  
  try {
    const response = await settingsApi.deleteKey(provider)
    if (response.success) {
      successMessage.value = `API key for ${provider} deleted`
      await fetchKeys()
    }
  } catch (err: unknown) {
    const axiosError = err as { response?: { data?: { message?: string } } }
    error.value = axiosError.response?.data?.message || 'Failed to delete API key'
  }
}

// Toggle API key status
const handleToggleKey = async (provider: Provider) => {
  try {
    const response = await settingsApi.toggleKey(provider)
    if (response.success) {
      await fetchKeys()
    }
  } catch (err: unknown) {
    const axiosError = err as { response?: { data?: { message?: string } } }
    error.value = axiosError.response?.data?.message || 'Failed to toggle API key'
  }
}

// Clear messages
const clearMessages = () => {
  error.value = null
  successMessage.value = null
}

// Initialize
onMounted(() => {
  fetchKeys()
  fetchStats()
})
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Profile Settings</h1>

    <!-- User info card -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
      <div class="flex items-center gap-4">
        <div class="w-16 h-16 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
          <span class="text-2xl font-bold text-primary-600 dark:text-primary-400">
            {{ authStore.username.charAt(0).toUpperCase() }}
          </span>
        </div>
        <div>
          <h2 class="text-xl font-semibold text-gray-900 dark:text-white">{{ authStore.username }}</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Member since {{ authStore.user?.created_at ? new Date(authStore.user.created_at).toLocaleDateString() : 'N/A' }}
          </p>
        </div>
      </div>

      <!-- Stats -->
      <div class="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
        <div class="text-center">
          <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ stats.documents.total }}</p>
          <p class="text-sm text-gray-500 dark:text-gray-400">Documents</p>
        </div>
        <div class="text-center">
          <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ stats.chat.sessions }}</p>
          <p class="text-sm text-gray-500 dark:text-gray-400">Chat Sessions</p>
        </div>
        <div class="text-center">
          <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ stats.api_keys }}</p>
          <p class="text-sm text-gray-500 dark:text-gray-400">API Keys</p>
        </div>
      </div>
    </div>

    <!-- API Keys section -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">LLM API Keys</h3>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
        Add your API keys to enable AI-powered features. Keys are stored securely.
      </p>

      <!-- Messages -->
      <div v-if="error" class="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
        <button @click="clearMessages" class="text-xs text-red-500 hover:underline mt-1">Dismiss</button>
      </div>
      
      <div v-if="successMessage" class="mb-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
        <p class="text-sm text-green-600 dark:text-green-400">{{ successMessage }}</p>
        <button @click="clearMessages" class="text-xs text-green-500 hover:underline mt-1">Dismiss</button>
      </div>

      <!-- Existing keys -->
      <div v-if="apiKeys.length > 0" class="space-y-3 mb-6">
        <div
          v-for="key in apiKeys"
          :key="key.id"
          class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-750 rounded-lg"
        >
          <div class="flex items-center gap-3">
            <div 
              class="w-3 h-3 rounded-full"
              :class="key.is_active ? 'bg-green-500' : 'bg-gray-400'"
            ></div>
            <div>
              <p class="font-medium text-gray-900 dark:text-white capitalize">{{ key.provider }}</p>
              <p class="text-sm text-gray-500 dark:text-gray-400 font-mono">{{ key.api_key_masked }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="handleToggleKey(key.provider)"
              class="px-3 py-1 text-sm rounded-lg border transition-colors"
              :class="key.is_active 
                ? 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                : 'border-green-300 text-green-600 hover:bg-green-50'"
            >
              {{ key.is_active ? 'Disable' : 'Enable' }}
            </button>
            <button
              @click="handleDeleteKey(key.provider)"
              class="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Add new key form -->
      <div class="border-t border-gray-200 dark:border-gray-700 pt-6">
        <h4 class="font-medium text-gray-900 dark:text-white mb-4">Add New API Key</h4>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <!-- Provider select -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Provider</label>
            <select
              v-model="newKey.provider"
              class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            >
              <option v-for="p in providers" :key="p.value" :value="p.value">
                {{ p.label }}
              </option>
            </select>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {{ providers.find(p => p.value === newKey.provider)?.description }}
            </p>
          </div>

          <!-- API Key input -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">API Key</label>
            <input
              v-model="newKey.api_key"
              type="password"
              placeholder="sk-..."
              class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>

        <button
          @click="handleSaveKey"
          :disabled="saving || !newKey.api_key.trim()"
          class="px-6 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center gap-2"
        >
          <svg v-if="saving" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ saving ? 'Saving...' : 'Save API Key' }}
        </button>
      </div>
    </div>

    <!-- Provider info -->
    <div class="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-6 border border-blue-200 dark:border-blue-800">
      <h4 class="font-medium text-blue-900 dark:text-blue-300 mb-2">Where to get API keys?</h4>
      <ul class="text-sm text-blue-800 dark:text-blue-400 space-y-2">
        <li>• <strong>Qwen:</strong> <a href="https://dashscope.console.aliyun.com/" target="_blank" class="underline">DashScope Console</a></li>
        <li>• <strong>DeepSeek:</strong> <a href="https://platform.deepseek.com/" target="_blank" class="underline">DeepSeek Platform</a></li>
        <li>• <strong>OpenAI:</strong> <a href="https://platform.openai.com/api-keys" target="_blank" class="underline">OpenAI Platform</a></li>
        <li>• <strong>Anthropic:</strong> <a href="https://console.anthropic.com/" target="_blank" class="underline">Anthropic Console</a></li>
      </ul>
    </div>
  </div>
</template>
