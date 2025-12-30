<script setup lang="ts">
/**
 * Files View (Knowledge Base)
 * 
 * Features:
 * - Drag & drop file upload
 * - File list with status indicators
 * - Delete and reparse actions
 */

import { ref, computed, onMounted } from 'vue'
import { useFilesStore } from '@/stores'
import type { FileDocument, ParsingStatus } from '@/types'

const filesStore = useFilesStore()

// State
const isDragging = ref(false)
const statusFilter = ref<ParsingStatus | ''>('')

// Computed
const files = computed(() => {
  if (!statusFilter.value) return filesStore.files
  return filesStore.files.filter(f => f.parsing_status === statusFilter.value)
})
const loading = computed(() => filesStore.loading)
const uploading = computed(() => filesStore.uploading)
const uploadProgress = computed(() => filesStore.uploadProgress)

// File type icons
const getFileIcon = (fileType: string): string => {
  switch (fileType.toLowerCase()) {
    case 'pdf':
      return 'M7 21h10a2 2 0 002-2V9l-5-5H7a2 2 0 00-2 2v13a2 2 0 002 2zm0-18h7l5 5v11a2 2 0 01-2 2H7a2 2 0 01-2-2V5a2 2 0 012-2z'
    case 'docx':
    case 'doc':
      return 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
    case 'md':
    case 'txt':
      return 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
    default:
      return 'M7 21h10a2 2 0 002-2V9l-5-5H7a2 2 0 00-2 2v13a2 2 0 002 2z'
  }
}

// Status badge styling
const getStatusBadge = (status: ParsingStatus) => {
  switch (status) {
    case 'completed':
      return { class: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300', text: 'Ready' }
    case 'processing':
      return { class: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300', text: 'Processing' }
    case 'pending':
      return { class: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300', text: 'Pending' }
    case 'failed':
      return { class: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300', text: 'Failed' }
    default:
      return { class: 'bg-gray-100 text-gray-700', text: status }
  }
}

// Format file size
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Format date
const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN')
}

// Handle drag events
const handleDragOver = (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = true
}

const handleDragLeave = () => {
  isDragging.value = false
}

const handleDrop = async (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = false
  
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    await uploadFiles(files)
  }
}

// Handle file input
const handleFileInput = async (e: Event) => {
  const input = e.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    await uploadFiles(input.files)
    input.value = '' // Reset input
  }
}

// Upload files
const uploadFiles = async (fileList: FileList) => {
  for (const file of Array.from(fileList)) {
    await filesStore.uploadFile(file)
  }
}

// Delete file
const handleDelete = async (file: FileDocument) => {
  if (confirm(`Are you sure you want to delete "${file.filename}"?`)) {
    await filesStore.deleteFile(file.id)
  }
}

// Reparse file
const handleReparse = async (file: FileDocument) => {
  await filesStore.reparseFile(file.id)
}

// Refresh file statuses
const refreshStatuses = async () => {
  for (const file of filesStore.files) {
    if (file.parsing_status === 'pending' || file.parsing_status === 'processing') {
      await filesStore.refreshFileStatus(file.id)
    }
  }
}

// Initialize
onMounted(() => {
  filesStore.fetchFiles(true)
  
  // Periodically refresh statuses for pending/processing files
  const interval = setInterval(refreshStatuses, 5000)
  return () => clearInterval(interval)
})
</script>

<template>
  <div class="max-w-5xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Knowledge Base</h1>

    <!-- Upload Area -->
    <div
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
      class="relative border-2 border-dashed rounded-xl p-8 mb-6 transition-colors text-center"
      :class="isDragging 
        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' 
        : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800'"
    >
      <!-- Upload progress overlay -->
      <div
        v-if="uploading"
        class="absolute inset-0 bg-white/90 dark:bg-gray-800/90 rounded-xl flex flex-col items-center justify-center z-10"
      >
        <div class="w-48 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-2">
          <div
            class="h-full bg-primary-600 transition-all duration-300"
            :style="{ width: `${uploadProgress}%` }"
          ></div>
        </div>
        <p class="text-sm text-gray-600 dark:text-gray-300">Uploading... {{ uploadProgress }}%</p>
      </div>

      <div class="flex flex-col items-center">
        <div class="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mb-4">
          <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
          </svg>
        </div>
        <p class="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
          Drag & drop files here
        </p>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
          or click to browse
        </p>
        <input
          type="file"
          @change="handleFileInput"
          accept=".pdf,.docx,.doc,.txt,.md,.pptx"
          multiple
          class="hidden"
          id="file-input"
        />
        <label
          for="file-input"
          class="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg cursor-pointer transition-colors"
        >
          Select Files
        </label>
        <p class="text-xs text-gray-400 dark:text-gray-500 mt-3">
          Supported: PDF, DOCX, DOC, TXT, MD, PPTX (max 50MB)
        </p>
      </div>
    </div>

    <!-- Filter -->
    <div class="flex items-center gap-4 mb-4">
      <label class="text-sm text-gray-600 dark:text-gray-400">Filter by status:</label>
      <select
        v-model="statusFilter"
        class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500"
      >
        <option value="">All</option>
        <option value="completed">Ready</option>
        <option value="processing">Processing</option>
        <option value="pending">Pending</option>
        <option value="failed">Failed</option>
      </select>
      
      <button
        @click="filesStore.fetchFiles(true)"
        :disabled="loading"
        class="ml-auto text-sm text-primary-600 dark:text-primary-400 hover:underline disabled:opacity-50"
      >
        Refresh
      </button>
    </div>

    <!-- File List -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
      <!-- Loading -->
      <div v-if="loading && files.length === 0" class="p-8">
        <div v-for="i in 3" :key="i" class="flex gap-4 mb-4 animate-pulse">
          <div class="w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
          <div class="flex-1">
            <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-2"></div>
            <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else-if="files.length === 0" class="p-12 text-center">
        <svg class="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
        </svg>
        <p class="text-gray-500 dark:text-gray-400">No documents yet</p>
        <p class="text-sm text-gray-400 dark:text-gray-500 mt-1">Upload your first document to get started</p>
      </div>

      <!-- File list -->
      <div v-else class="divide-y divide-gray-200 dark:divide-gray-700">
        <div
          v-for="file in files"
          :key="file.id"
          class="p-4 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors flex items-center gap-4"
        >
          <!-- File icon -->
          <div class="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center flex-shrink-0">
            <svg class="w-6 h-6 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" :d="getFileIcon(file.file_type)"/>
            </svg>
          </div>

          <!-- File info -->
          <div class="flex-1 min-w-0">
            <p class="font-medium text-gray-900 dark:text-white truncate">{{ file.filename }}</p>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              {{ formatFileSize(file.file_size) }} · {{ formatDate(file.upload_time) }}
              <span v-if="file.chunk_count > 0"> · {{ file.chunk_count }} chunks</span>
            </p>
            <p v-if="file.parsing_error" class="text-xs text-red-500 mt-1">{{ file.parsing_error }}</p>
          </div>

          <!-- Status badge -->
          <span
            class="px-2.5 py-1 text-xs font-medium rounded-full"
            :class="getStatusBadge(file.parsing_status).class"
          >
            {{ getStatusBadge(file.parsing_status).text }}
          </span>

          <!-- Actions -->
          <div class="flex items-center gap-2">
            <!-- Reparse button (for failed files) -->
            <button
              v-if="file.parsing_status === 'failed'"
              @click="handleReparse(file)"
              class="p-2 text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
              title="Retry parsing"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
            </button>

            <!-- Delete button -->
            <button
              @click="handleDelete(file)"
              class="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
              title="Delete"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Load more -->
      <div v-if="filesStore.hasMore" class="p-4 border-t border-gray-200 dark:border-gray-700 text-center">
        <button
          @click="filesStore.fetchFiles()"
          :disabled="loading"
          class="text-sm text-primary-600 dark:text-primary-400 hover:underline disabled:opacity-50"
        >
          {{ loading ? 'Loading...' : 'Load more' }}
        </button>
      </div>
    </div>
  </div>
</template>
