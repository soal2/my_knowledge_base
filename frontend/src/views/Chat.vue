<script setup lang="ts">
/**
 * Chat View
 * 
 * Features:
 * - Chat container with auto-scroll
 * - Message input with deep thinking toggle
 * - Model selection dropdown
 * - Markdown rendering for AI responses
 * - Support for math formulas and code blocks
 */

import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useChatStore, useFilesStore } from '@/stores'
import { useMarkdown } from '@/composables/useMarkdown'
import { settingsApi } from '@/api'
import type { ChatMessage, AvailableModel, AvailableModels } from '@/types'

const chatStore = useChatStore()
const filesStore = useFilesStore()
const { render: renderMarkdown } = useMarkdown()

// Refs
const messagesContainer = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)

// State
const message = ref('')
const isDeepThought = ref(false)
const selectedDocIds = ref<number[]>([])
const showDocSelect = ref(false)
const showModelSelect = ref(false)
const availableModels = ref<AvailableModels>({} as AvailableModels)
const selectedModel = ref<string>('')
const loadingModels = ref(false)

// Computed
const messages = computed(() => chatStore.messages)
const sending = computed(() => chatStore.sending)
const currentSession = computed(() => chatStore.currentSession)
const completedFiles = computed(() => filesStore.completedFiles)

// Flatten all models into a single list with provider info
const allModels = computed(() => {
  const models: (AvailableModel & { provider: string })[] = []
  for (const [provider, providerModels] of Object.entries(availableModels.value)) {
    for (const model of providerModels as AvailableModel[]) {
      models.push({ ...model, provider })
    }
  }
  return models
})

// Get selected model display name
const selectedModelName = computed(() => {
  if (!selectedModel.value) return 'Select model'
  const model = allModels.value.find(m => m.id === selectedModel.value)
  return model ? model.name : selectedModel.value
})

// Auto-scroll to bottom
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// Watch messages for auto-scroll
watch(messages, () => {
  scrollToBottom()
}, { deep: true })

// Send message
const handleSend = async () => {
  const trimmedMessage = message.value.trim()
  if (!trimmedMessage || sending.value) return
  
  // If no session, create one first
  if (!currentSession.value) {
    await chatStore.createSession(trimmedMessage.slice(0, 50))
  }
  
  // Clear input immediately
  const messageToSend = trimmedMessage
  message.value = ''
  
  // Send message with model selection
  await chatStore.sendMessage({
    message: messageToSend,
    is_deep_thought: isDeepThought.value,
    doc_ids: selectedDocIds.value.length > 0 ? selectedDocIds.value : undefined,
    model: selectedModel.value || undefined
  })
  
  // Focus input
  inputRef.value?.focus()
}

// Handle key press
const handleKeyPress = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

// Toggle document selection
const toggleDocSelect = () => {
  showDocSelect.value = !showDocSelect.value
  if (showDocSelect.value && filesStore.files.length === 0) {
    filesStore.fetchFiles(true)
  }
}

// Toggle document in selection
const toggleDocument = (docId: number) => {
  const index = selectedDocIds.value.indexOf(docId)
  if (index === -1) {
    selectedDocIds.value.push(docId)
  } else {
    selectedDocIds.value.splice(index, 1)
  }
}

// Format message time
const formatTime = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// Get rendered content
const getRenderedContent = (msg: ChatMessage): string => {
  return renderMarkdown(msg.content)
}

// Fetch available models
const fetchModels = async () => {
  loadingModels.value = true
  try {
    const response = await settingsApi.getModels()
    if (response.success) {
      availableModels.value = response.data
      // Auto-select first model if none selected
      if (!selectedModel.value && allModels.value.length > 0) {
        selectedModel.value = allModels.value[0].id
      }
    }
  } catch (err) {
    console.error('Failed to fetch models:', err)
  } finally {
    loadingModels.value = false
  }
}

// Toggle model selection dropdown
const toggleModelSelect = () => {
  showModelSelect.value = !showModelSelect.value
  if (showModelSelect.value && Object.keys(availableModels.value).length === 0) {
    fetchModels()
  }
}

// Select a model
const selectModel = (modelId: string) => {
  selectedModel.value = modelId
  showModelSelect.value = false
}

// Initialize
onMounted(() => {
  scrollToBottom()
  inputRef.value?.focus()
  fetchModels() // Load available models on mount
})
</script>

<template>
  <div class="h-[calc(100vh-7rem)] flex flex-col">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-semibold text-gray-900 dark:text-white">
        {{ currentSession?.title || 'New Chat' }}
      </h1>
      
      <div class="flex items-center gap-2">
        <!-- Model selector -->
        <div class="relative">
          <button
            @click="toggleModelSelect"
            class="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            :class="{ 'bg-primary-100 dark:bg-primary-900 border-primary-500': selectedModel }"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
            </svg>
            <span class="max-w-[120px] truncate">{{ selectedModelName }}</span>
            <svg class="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>
          
          <!-- Model dropdown -->
          <div
            v-if="showModelSelect"
            class="absolute right-0 top-full mt-2 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10 max-h-80 overflow-y-auto"
          >
            <div v-if="loadingModels" class="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
              Loading models...
            </div>
            <div v-else-if="allModels.length === 0" class="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
              <p>No models available</p>
              <p class="text-xs mt-1">Add API keys in Profile settings</p>
            </div>
            <div v-else class="p-2">
              <div v-for="(models, provider) in availableModels" :key="provider" class="mb-2">
                <div class="px-3 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                  {{ provider }}
                </div>
                <button
                  v-for="model in models"
                  :key="model.id"
                  @click="selectModel(model.id)"
                  class="w-full flex flex-col px-3 py-2 rounded-lg text-left hover:bg-gray-100 dark:hover:bg-gray-700"
                  :class="{ 'bg-primary-100 dark:bg-primary-900': selectedModel === model.id }"
                >
                  <span class="text-sm font-medium text-gray-900 dark:text-white">{{ model.name }}</span>
                  <span class="text-xs text-gray-500 dark:text-gray-400">{{ model.description }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Document selector toggle -->
        <div class="relative">
          <button
            @click="toggleDocSelect"
            class="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            :class="{ 'bg-primary-100 dark:bg-primary-900 border-primary-500': selectedDocIds.length > 0 }"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            <span>
              {{ selectedDocIds.length > 0 ? `${selectedDocIds.length} docs` : 'Select docs' }}
            </span>
          </button>
        
        <!-- Document dropdown -->
        <div
          v-if="showDocSelect"
          class="absolute right-0 top-full mt-2 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10 max-h-64 overflow-y-auto"
        >
          <div v-if="completedFiles.length === 0" class="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
            No parsed documents
          </div>
          <div v-else class="p-2 space-y-1">
            <button
              v-for="file in completedFiles"
              :key="file.id"
              @click="toggleDocument(file.id)"
              class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
              :class="{ 'bg-primary-100 dark:bg-primary-900': selectedDocIds.includes(file.id) }"
            >
              <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <span class="truncate">{{ file.filename }}</span>
              <svg
                v-if="selectedDocIds.includes(file.id)"
                class="w-4 h-4 ml-auto text-primary-600"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
              </svg>
            </button>
          </div>
        </div>
        </div>
      </div>
    </div>

    <!-- Messages container -->
    <div 
      ref="messagesContainer"
      class="flex-1 overflow-y-auto bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700"
    >
      <!-- Empty state -->
      <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center p-8">
        <div class="w-20 h-20 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center mb-4">
          <svg class="w-10 h-10 text-primary-600 dark:text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
          </svg>
        </div>
        <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">Start a conversation</h2>
        <p class="text-gray-500 dark:text-gray-400 text-center max-w-md">
          Ask questions about your uploaded documents or discuss any topic. 
          Enable "Deep Thinking" for complex analysis.
        </p>
      </div>

      <!-- Message list -->
      <div v-else class="p-4 space-y-4">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="flex gap-3"
          :class="{ 'flex-row-reverse': msg.role === 'user' }"
        >
          <!-- Avatar -->
          <div
            class="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center"
            :class="msg.role === 'user' 
              ? 'bg-primary-600 text-white' 
              : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'"
          >
            <svg v-if="msg.role === 'user'" class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
            </svg>
            <svg v-else class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
            </svg>
          </div>

          <!-- Message content -->
          <div
            class="max-w-[80%] rounded-2xl px-4 py-3"
            :class="msg.role === 'user'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'"
          >
            <!-- Deep thought indicator -->
            <div v-if="msg.is_deep_thought && msg.role === 'ai'" class="flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 mb-2">
              <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
              <span>Deep Thinking</span>
            </div>

            <!-- Thinking content (expandable) -->
            <details v-if="msg.thinking_content" class="mb-2">
              <summary class="text-xs text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300">
                Show reasoning process
              </summary>
              <div class="mt-2 p-2 bg-gray-200 dark:bg-gray-600 rounded text-sm text-gray-700 dark:text-gray-300">
                {{ msg.thinking_content }}
              </div>
            </details>

            <!-- Message content -->
            <div 
              v-if="msg.role === 'ai'"
              class="markdown-body prose prose-sm dark:prose-invert max-w-none"
              v-html="getRenderedContent(msg)"
            ></div>
            <div v-else class="whitespace-pre-wrap">{{ msg.content }}</div>

            <!-- Time & tokens -->
            <div 
              class="mt-2 text-xs opacity-60"
              :class="msg.role === 'user' ? 'text-right' : ''"
            >
              {{ formatTime(msg.created_at) }}
              <span v-if="msg.tokens_used"> · {{ msg.tokens_used }} tokens</span>
            </div>
          </div>
        </div>

        <!-- Sending indicator -->
        <div v-if="sending" class="flex gap-3">
          <div class="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
            <svg class="w-4 h-4 text-gray-600 dark:text-gray-300" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
            </svg>
          </div>
          <div class="bg-gray-100 dark:bg-gray-700 rounded-2xl px-4 py-3">
            <div class="flex gap-1">
              <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
              <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
              <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Input area -->
    <div class="mt-4 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
      <!-- Deep thinking toggle -->
      <div class="flex items-center justify-between mb-3">
        <label class="flex items-center gap-2 cursor-pointer">
          <div 
            class="relative w-10 h-5 rounded-full transition-colors"
            :class="isDeepThought ? 'bg-primary-600' : 'bg-gray-300 dark:bg-gray-600'"
            @click="isDeepThought = !isDeepThought"
          >
            <div 
              class="absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform shadow"
              :class="isDeepThought ? 'translate-x-5' : 'translate-x-0.5'"
            ></div>
          </div>
          <span class="text-sm text-gray-700 dark:text-gray-300">
            深度思考 (Deep Thinking)
          </span>
        </label>

        <!-- Selected docs indicator -->
        <div v-if="selectedDocIds.length > 0" class="text-xs text-gray-500 dark:text-gray-400">
          Searching in {{ selectedDocIds.length }} document(s)
        </div>
      </div>

      <!-- Input & send button -->
      <div class="flex gap-3">
        <textarea
          ref="inputRef"
          v-model="message"
          @keydown="handleKeyPress"
          rows="1"
          placeholder="Ask about your documents..."
          class="flex-1 resize-none px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors"
          :disabled="sending"
        ></textarea>
        
        <button
          @click="handleSend"
          :disabled="!message.trim() || sending"
          class="px-6 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center gap-2"
        >
          <svg v-if="sending" class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
          </svg>
          <span class="hidden sm:inline">Send</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style>
/* Additional highlight.js styles for dark mode */
.dark .hljs {
  background: #1f2937;
  color: #e5e7eb;
}
</style>
