/**
 * Chat Store
 * Manages chat sessions and messages
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { chatApi } from '@/api'
import type { ChatSession, ChatMessage, SendMessageRequest } from '@/types'

export const useChatStore = defineStore('chat', () => {
  // State
  const sessions = ref<ChatSession[]>([])
  const currentSession = ref<ChatSession | null>(null)
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const sending = ref(false)
  const streamingContent = ref('')
  const error = ref<string | null>(null)

  // Pagination
  const page = ref(1)
  const hasMore = ref(true)

  // Getters
  const sortedSessions = computed(() => {
    return [...sessions.value].sort((a, b) => 
      new Date(b.last_active_at).getTime() - new Date(a.last_active_at).getTime()
    )
  })

  const currentSessionId = computed(() => currentSession.value?.id || null)

  // Actions
  async function fetchSessions(reset = false): Promise<void> {
    if (reset) {
      page.value = 1
      hasMore.value = true
    }
    
    if (!hasMore.value) return
    
    loading.value = true
    error.value = null
    
    try {
      const response = await chatApi.getHistory(page.value)
      if (response.success) {
        if (reset) {
          sessions.value = response.data
        } else {
          sessions.value.push(...response.data)
        }
        hasMore.value = response.pagination.has_next
        page.value++
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { message?: string } } }
      error.value = axiosError.response?.data?.message || 'Failed to fetch sessions'
    } finally {
      loading.value = false
    }
  }

  async function createSession(title?: string, initialMessage?: string): Promise<number | null> {
    loading.value = true
    error.value = null
    
    try {
      const response = await chatApi.createSession({ title, initial_message: initialMessage })
      if (response.success) {
        const newSession = response.data
        sessions.value.unshift(newSession)
        currentSession.value = newSession
        messages.value = []
        return newSession.id
      }
      return null
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { message?: string } } }
      error.value = axiosError.response?.data?.message || 'Failed to create session'
      return null
    } finally {
      loading.value = false
    }
  }

  async function loadSession(sessionId: number): Promise<boolean> {
    loading.value = true
    error.value = null
    
    try {
      const response = await chatApi.getSession(sessionId)
      if (response.success) {
        currentSession.value = response.data.session
        messages.value = response.data.messages
        return true
      }
      return false
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { message?: string } } }
      error.value = axiosError.response?.data?.message || 'Failed to load session'
      return false
    } finally {
      loading.value = false
    }
  }

  async function deleteSession(sessionId: number): Promise<boolean> {
    try {
      const response = await chatApi.deleteSession(sessionId)
      if (response.success) {
        sessions.value = sessions.value.filter(s => s.id !== sessionId)
        if (currentSession.value?.id === sessionId) {
          currentSession.value = null
          messages.value = []
        }
        return true
      }
      return false
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { message?: string } } }
      error.value = axiosError.response?.data?.message || 'Failed to delete session'
      return false
    }
  }

  async function sendMessage(data: SendMessageRequest): Promise<boolean> {
    if (!currentSession.value) return false
    
    sending.value = true
    error.value = null
    streamingContent.value = ''
    
    // Add user message immediately
    const userMessage: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: data.message,
      is_deep_thought: data.is_deep_thought || false,
      thinking_content: null,
      tokens_used: 0,
      created_at: new Date().toISOString()
    }
    messages.value.push(userMessage)
    
    try {
      const response = await chatApi.sendMessage(currentSession.value.id, data)
      if (response.success) {
        messages.value.push(response.data)
        return true
      }
      return false
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { message?: string } } }
      error.value = axiosError.response?.data?.message || 'Failed to send message'
      // Remove user message on error
      messages.value.pop()
      return false
    } finally {
      sending.value = false
    }
  }

  function clearCurrentSession(): void {
    currentSession.value = null
    messages.value = []
    streamingContent.value = ''
  }

  return {
    // State
    sessions,
    currentSession,
    messages,
    loading,
    sending,
    streamingContent,
    error,
    hasMore,
    // Getters
    sortedSessions,
    currentSessionId,
    // Actions
    fetchSessions,
    createSession,
    loadSession,
    deleteSession,
    sendMessage,
    clearCurrentSession
  }
})
