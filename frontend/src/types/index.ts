/**
 * TypeScript interfaces for API responses and data models
 * Based on API_DOCUMENTATION.md
 */

// ============================================================================
// Generic API Response Types
// ============================================================================

export interface ApiResponse<T = unknown> {
  success: boolean
  message: string
  data: T
  errors?: Record<string, string>
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number
    per_page: number
    total: number
    total_pages: number
    has_next: boolean
    has_prev: boolean
  }
}

// ============================================================================
// Auth Types
// ============================================================================

export interface User {
  id: number
  username: string
  created_at: string
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface RegisterCredentials {
  username: string
  password: string
  confirm_password?: string
}

export interface AuthResponse {
  user: User
  access_token: string
  refresh_token: string
}

export interface TokenRefreshResponse {
  access_token: string
  refresh_token: string
}

// ============================================================================
// API Key Types
// ============================================================================

export type Provider = 'qwen' | 'deepseek' | 'openai' | 'anthropic'

export interface APIKey {
  id: number
  provider: Provider
  api_key_masked: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SaveAPIKeyRequest {
  provider: Provider
  api_key: string
}

// ============================================================================
// Chat Types
// ============================================================================

export type MessageRole = 'user' | 'ai' | 'system'

export interface ChatMessage {
  id: number
  role: MessageRole
  content: string
  is_deep_thought: boolean
  thinking_content: string | null
  tokens_used: number
  created_at: string
}

export interface ChatSession {
  id: number
  title: string
  message_count?: number
  preview?: string
  created_at: string
  last_active_at: string
}

export interface ChatSessionDetail {
  session: ChatSession
  messages: ChatMessage[]
}

export interface CreateSessionRequest {
  title?: string
  initial_message?: string
}

export interface SendMessageRequest {
  message: string
  is_deep_thought?: boolean
  doc_ids?: number[]
  model?: string  // e.g., 'qwen-plus', 'deepseek-chat'
}

// ============================================================================
// File Types
// ============================================================================

export type ParsingStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface FileDocument {
  id: number
  filename: string
  file_type: string
  file_size: number
  parsing_status: ParsingStatus
  parsing_error: string | null
  chunk_count: number
  upload_time: string
  parsed_at: string | null
}

export interface FileUploadResponse {
  id: number
  filename: string
  file_type: string
  file_size: number
  parsing_status: ParsingStatus
  upload_time: string
}

// ============================================================================
// Stats Types
// ============================================================================

export interface UserStats {
  documents: {
    total: number
    completed: number
  }
  chat: {
    sessions: number
    messages: number
  }
  api_keys: number
}

// ============================================================================
// Model Types
// ============================================================================

export interface AvailableModel {
  id: string       // e.g., 'qwen-plus', 'deepseek-chat'
  name: string     // e.g., 'Qwen Plus'
  description: string
}

export type AvailableModels = Record<Provider, AvailableModel[]>
