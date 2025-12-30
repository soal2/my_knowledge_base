/**
 * Auth API endpoints
 * Based on API_DOCUMENTATION.md Section 4
 */

import apiClient, { setTokens, clearTokens } from './client'
import type { 
  ApiResponse, 
  AuthResponse, 
  LoginCredentials, 
  RegisterCredentials,
  User 
} from '@/types'

export const authApi = {
  /**
   * Register a new user
   * POST /auth/register
   */
  async register(credentials: RegisterCredentials): Promise<ApiResponse<AuthResponse>> {
    const response = await apiClient.post<ApiResponse<AuthResponse>>(
      '/auth/register',
      credentials
    )
    if (response.data.success) {
      setTokens(response.data.data.access_token, response.data.data.refresh_token)
    }
    return response.data
  },

  /**
   * Login user
   * POST /auth/login
   */
  async login(credentials: LoginCredentials): Promise<ApiResponse<AuthResponse>> {
    const response = await apiClient.post<ApiResponse<AuthResponse>>(
      '/auth/login',
      credentials
    )
    if (response.data.success) {
      setTokens(response.data.data.access_token, response.data.data.refresh_token)
    }
    return response.data
  },

  /**
   * Get current user info
   * GET /auth/me
   */
  async me(): Promise<ApiResponse<User>> {
    const response = await apiClient.get<ApiResponse<User>>('/auth/me')
    return response.data
  },

  /**
   * Logout user
   * POST /auth/logout
   */
  async logout(): Promise<ApiResponse<null>> {
    try {
      const response = await apiClient.post<ApiResponse<null>>('/auth/logout')
      return response.data
    } finally {
      clearTokens()
    }
  },

  /**
   * Change password
   * POST /auth/change-password
   */
  async changePassword(data: {
    current_password: string
    new_password: string
    confirm_password: string
  }): Promise<ApiResponse<{ access_token: string; refresh_token: string }>> {
    const response = await apiClient.post<ApiResponse<{ access_token: string; refresh_token: string }>>(
      '/auth/change-password',
      data
    )
    if (response.data.success) {
      setTokens(response.data.data.access_token, response.data.data.refresh_token)
    }
    return response.data
  }
}
