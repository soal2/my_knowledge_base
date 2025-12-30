/**
 * Files Store
 * Manages document files
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { filesApi } from '@/api'
import type { FileDocument, ParsingStatus } from '@/types'

export const useFilesStore = defineStore('files', () => {
  // State
  const files = ref<FileDocument[]>([])
  const loading = ref(false)
  const uploading = ref(false)
  const uploadProgress = ref(0)
  const error = ref<string | null>(null)

  // Pagination
  const page = ref(1)
  const hasMore = ref(true)

  // Getters
  const completedFiles = computed(() => 
    files.value.filter(f => f.parsing_status === 'completed')
  )

  const pendingFiles = computed(() => 
    files.value.filter(f => f.parsing_status === 'pending' || f.parsing_status === 'processing')
  )

  const failedFiles = computed(() => 
    files.value.filter(f => f.parsing_status === 'failed')
  )

  // Actions
  async function fetchFiles(reset = false, status?: ParsingStatus): Promise<void> {
    if (reset) {
      page.value = 1
      hasMore.value = true
    }
    
    if (!hasMore.value) return
    
    loading.value = true
    error.value = null
    
    try {
      const response = await filesApi.getList(page.value, 20, status)
      if (response.success) {
        if (reset) {
          files.value = response.data
        } else {
          files.value.push(...response.data)
        }
        hasMore.value = response.pagination.has_next
        page.value++
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { message?: string } } }
      error.value = axiosError.response?.data?.message || 'Failed to fetch files'
    } finally {
      loading.value = false
    }
  }

  async function uploadFile(file: File): Promise<boolean> {
    uploading.value = true
    uploadProgress.value = 0
    error.value = null
    
    try {
      const response = await filesApi.upload(file, (percent) => {
        uploadProgress.value = percent
      })
      
      if (response.success) {
        // Add to files list
        const newFile: FileDocument = {
          ...response.data,
          parsing_error: null,
          chunk_count: 0,
          parsed_at: null
        }
        files.value.unshift(newFile)
        return true
      }
      return false
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { message?: string } } }
      error.value = axiosError.response?.data?.message || 'Upload failed'
      return false
    } finally {
      uploading.value = false
      uploadProgress.value = 0
    }
  }

  async function deleteFile(docId: number): Promise<boolean> {
    try {
      const response = await filesApi.deleteFile(docId)
      if (response.success) {
        files.value = files.value.filter(f => f.id !== docId)
        return true
      }
      return false
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { message?: string } } }
      error.value = axiosError.response?.data?.message || 'Failed to delete file'
      return false
    }
  }

  async function refreshFileStatus(docId: number): Promise<void> {
    try {
      const response = await filesApi.getStatus(docId)
      if (response.success) {
        const index = files.value.findIndex(f => f.id === docId)
        if (index !== -1) {
          files.value[index] = {
            ...files.value[index],
            parsing_status: response.data.parsing_status,
            parsing_error: response.data.parsing_error,
            chunk_count: response.data.chunk_count,
            parsed_at: response.data.parsed_at
          }
        }
      }
    } catch {
      // Silently fail
    }
  }

  async function reparseFile(docId: number): Promise<boolean> {
    try {
      const response = await filesApi.reparse(docId)
      if (response.success) {
        const index = files.value.findIndex(f => f.id === docId)
        if (index !== -1) {
          files.value[index].parsing_status = response.data.parsing_status
        }
        return true
      }
      return false
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { message?: string } } }
      error.value = axiosError.response?.data?.message || 'Failed to reparse file'
      return false
    }
  }

  return {
    // State
    files,
    loading,
    uploading,
    uploadProgress,
    error,
    hasMore,
    // Getters
    completedFiles,
    pendingFiles,
    failedFiles,
    // Actions
    fetchFiles,
    uploadFile,
    deleteFile,
    refreshFileStatus,
    reparseFile
  }
})
