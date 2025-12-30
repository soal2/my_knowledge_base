/**
 * Settings API endpoints (API Keys)
 * Based on API_DOCUMENTATION.md Section 5
 */

import apiClient from './client'
import type { 
  ApiResponse, 
  APIKey,
  SaveAPIKeyRequest,
  UserStats,
  Provider,
  AvailableModels
} from '@/types'

export const settingsApi = {
  /**
   * Get all API keys
   * GET /api/settings/keys
   */
  async getKeys(): Promise<ApiResponse<APIKey[]>> {
    const response = await apiClient.get<ApiResponse<APIKey[]>>('/api/settings/keys')
    return response.data
  },

  /**
   * Save or update an API key
   * POST /api/settings/keys
   */
  async saveKey(data: SaveAPIKeyRequest): Promise<ApiResponse<{ provider: Provider }>> {
    const response = await apiClient.post<ApiResponse<{ provider: Provider }>>(
      '/api/settings/keys',
      data
    )
    return response.data
  },

  /**
   * Delete an API key
   * DELETE /api/settings/keys/:provider
   */
  async deleteKey(provider: Provider): Promise<ApiResponse<null>> {
    const response = await apiClient.delete<ApiResponse<null>>(
      `/api/settings/keys/${provider}`
    )
    return response.data
  },

  /**
   * Toggle API key active status
   * POST /api/settings/keys/:provider/toggle
   */
  async toggleKey(provider: Provider): Promise<ApiResponse<{ is_active: boolean }>> {
    const response = await apiClient.post<ApiResponse<{ is_active: boolean }>>(
      `/api/settings/keys/${provider}/toggle`
    )
    return response.data
  },

  /**
   * Get user statistics
   * GET /api/stats
   */
  async getStats(): Promise<ApiResponse<UserStats>> {
    const response = await apiClient.get<ApiResponse<UserStats>>('/api/stats')
    return response.data
  },

  /**
   * Get available models for user's configured providers
   * GET /api/settings/models
   */
  async getModels(): Promise<ApiResponse<AvailableModels>> {
    const response = await apiClient.get<ApiResponse<AvailableModels>>('/api/settings/models')
    return response.data
  }
}
