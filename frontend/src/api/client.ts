/**
 * Axios API Client with JWT Interceptor
 * 
 * Features:
 * - Automatic Bearer token attachment
 * - Token refresh on 401
 * - Request/Response error handling
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'
import type { ApiResponse, TokenRefreshResponse } from '@/types'

// Base URL - use proxy in development
const BASE_URL = import.meta.env.PROD ? 'http://localhost:5001' : ''

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 30000
})

// Token storage keys
const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

// Token management functions
export const getAccessToken = (): string | null => {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export const getRefreshToken = (): string | null => {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export const setTokens = (accessToken: string, refreshToken: string): void => {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
}

export const clearTokens = (): void => {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

// Flag to prevent multiple refresh attempts
let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

const subscribeTokenRefresh = (callback: (token: string) => void) => {
  refreshSubscribers.push(callback)
}

const onTokenRefreshed = (token: string) => {
  refreshSubscribers.forEach(callback => callback(token))
  refreshSubscribers = []
}

// Request interceptor - attach Bearer token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

// Response interceptor - handle 401 and refresh token
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiResponse>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    
    // If 401 and not a refresh request, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = getRefreshToken()
      
      // If no refresh token or this is already a retry, clear tokens and redirect
      if (!refreshToken || originalRequest.url?.includes('/auth/refresh')) {
        clearTokens()
        window.location.href = '/login'
        return Promise.reject(error)
      }
      
      if (isRefreshing) {
        // Wait for token refresh
        return new Promise((resolve) => {
          subscribeTokenRefresh((token: string) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`
            }
            resolve(apiClient(originalRequest))
          })
        })
      }
      
      originalRequest._retry = true
      isRefreshing = true
      
      try {
        const response = await axios.post<ApiResponse<TokenRefreshResponse>>(
          `${BASE_URL}/auth/refresh`,
          {},
          {
            headers: {
              Authorization: `Bearer ${refreshToken}`
            }
          }
        )
        
        const { access_token, refresh_token } = response.data.data
        setTokens(access_token, refresh_token)
        
        isRefreshing = false
        onTokenRefreshed(access_token)
        
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`
        }
        
        return apiClient(originalRequest)
      } catch (refreshError) {
        isRefreshing = false
        clearTokens()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }
    
    return Promise.reject(error)
  }
)

export default apiClient
