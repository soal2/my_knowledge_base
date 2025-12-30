<script setup lang="ts">
/**
 * Sidebar Component
 * 
 * Features:
 * - Chat history list
 * - New chat button
 * - Session management
 */

import { onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useChatStore } from '@/stores'

const router = useRouter()
const route = useRoute()
const chatStore = useChatStore()

const sessions = computed(() => chatStore.sortedSessions)
const loading = computed(() => chatStore.loading)
const currentSessionId = computed(() => chatStore.currentSessionId)

// Format date for display
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } else if (days === 1) {
    return 'Yesterday'
  } else if (days < 7) {
    return `${days} days ago`
  } else {
    return date.toLocaleDateString('zh-CN')
  }
}

// Create new chat
const handleNewChat = async () => {
  const sessionId = await chatStore.createSession()
  if (sessionId && route.path !== '/') {
    router.push('/')
  }
}

// Load a session
const handleSelectSession = async (sessionId: number) => {
  if (currentSessionId.value !== sessionId) {
    await chatStore.loadSession(sessionId)
    if (route.path !== '/') {
      router.push('/')
    }
  }
}

// Delete a session
const handleDeleteSession = async (sessionId: number, event: Event) => {
  event.stopPropagation()
  if (confirm('Are you sure you want to delete this chat?')) {
    await chatStore.deleteSession(sessionId)
  }
}

// Fetch sessions on mount
onMounted(() => {
  chatStore.fetchSessions(true)
})
</script>

<template>
  <aside class="fixed left-0 top-16 bottom-0 w-64 bg-gray-100 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col">
    <!-- New Chat Button -->
    <div class="p-3">
      <button
        @click="handleNewChat"
        class="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        <span>New Chat</span>
      </button>
    </div>

    <!-- Chat History -->
    <div class="flex-1 overflow-y-auto">
      <div class="px-3 py-2">
        <h3 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
          Chat History
        </h3>
      </div>

      <!-- Loading state -->
      <div v-if="loading && sessions.length === 0" class="px-3">
        <div v-for="i in 5" :key="i" class="h-12 bg-gray-200 dark:bg-gray-700 rounded-lg mb-2 animate-pulse"></div>
      </div>

      <!-- Empty state -->
      <div v-else-if="sessions.length === 0" class="px-3 py-8 text-center">
        <svg class="w-12 h-12 mx-auto text-gray-400 dark:text-gray-500 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
        </svg>
        <p class="text-sm text-gray-500 dark:text-gray-400">No chats yet</p>
        <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">Start a new conversation</p>
      </div>

      <!-- Session list -->
      <div v-else class="space-y-1 px-2">
        <button
          v-for="session in sessions"
          :key="session.id"
          @click="handleSelectSession(session.id)"
          class="w-full group flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors"
          :class="currentSessionId === session.id 
            ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300' 
            : 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'"
        >
          <!-- Chat icon -->
          <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
          </svg>
          
          <!-- Title & date -->
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium truncate">{{ session.title }}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400 truncate">
              {{ formatDate(session.last_active_at) }}
            </p>
          </div>

          <!-- Delete button -->
          <button
            @click="handleDeleteSession(session.id, $event)"
            class="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500 transition-all"
            title="Delete"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
          </button>
        </button>
      </div>
    </div>

    <!-- Load more -->
    <div v-if="chatStore.hasMore" class="p-3 border-t border-gray-200 dark:border-gray-700">
      <button
        @click="chatStore.fetchSessions()"
        :disabled="loading"
        class="w-full text-sm text-primary-600 dark:text-primary-400 hover:underline disabled:opacity-50"
      >
        {{ loading ? 'Loading...' : 'Load more' }}
      </button>
    </div>
  </aside>
</template>
