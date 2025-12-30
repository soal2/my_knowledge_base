/**
 * Files API endpoints
 * Based on API_DOCUMENTATION.md Section 6
 */

import apiClient from './client'
import type { 
  ApiResponse, 
  PaginatedResponse,
  FileDocument,
  FileUploadResponse,
  ParsingStatus
} from '@/types'

export const filesApi = {
  /**
   * Upload a file
   * POST /files/upload
   */
  async upload(file: File, onProgress?: (percent: number) => void): Promise<ApiResponse<FileUploadResponse>> {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await apiClient.post<ApiResponse<FileUploadResponse>>(
      '/files/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            onProgress(percent)
          }
        }
      }
    )
    return response.data
  },

  /**
   * Get file list with pagination
   * GET /files/list
   */
  async getList(
    page = 1, 
    perPage = 20, 
    status?: ParsingStatus
  ): Promise<PaginatedResponse<FileDocument>> {
    const params: Record<string, unknown> = { page, per_page: perPage }
    if (status) {
      params.status = status
    }
    
    const response = await apiClient.get<PaginatedResponse<FileDocument>>(
      '/files/list',
      { params }
    )
    return response.data
  },

  /**
   * Get file details
   * GET /files/:docId
   */
  async getFile(docId: number): Promise<ApiResponse<FileDocument>> {
    const response = await apiClient.get<ApiResponse<FileDocument>>(
      `/files/${docId}`
    )
    return response.data
  },

  /**
   * Delete a file
   * DELETE /files/:docId
   */
  async deleteFile(docId: number): Promise<ApiResponse<null>> {
    const response = await apiClient.delete<ApiResponse<null>>(
      `/files/${docId}`
    )
    return response.data
  },

  /**
   * Get parsing status
   * GET /files/:docId/status
   */
  async getStatus(docId: number): Promise<ApiResponse<{
    id: number
    filename: string
    parsing_status: ParsingStatus
    parsing_error: string | null
    chunk_count: number
    parsed_at: string | null
  }>> {
    const response = await apiClient.get(`/files/${docId}/status`)
    return response.data
  },

  /**
   * Reparse a file
   * POST /files/:docId/reparse
   */
  async reparse(docId: number): Promise<ApiResponse<{ id: number; parsing_status: ParsingStatus }>> {
    const response = await apiClient.post(`/files/${docId}/reparse`)
    return response.data
  }
}
