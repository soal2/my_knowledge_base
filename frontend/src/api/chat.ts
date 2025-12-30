/**
 * Chat API endpoints
 * Based on API_DOCUMENTATION.md Section 5
 */

import apiClient from './client'
import type { 
  ApiResponse, 
  PaginatedResponse,
  ChatSession,
  ChatSessionDetail,
  CreateSessionRequest,
  SendMessageRequest,
  ChatMessage
} from '@/types'

export const chatApi = {
  /**
   * Get chat history (sessions list)
   * GET /api/history
   */
  async getHistory(page = 1, perPage = 20): Promise<PaginatedResponse<ChatSession>> {
    const response = await apiClient.get<PaginatedResponse<ChatSession>>(
      '/api/history',
      { params: { page, per_page: perPage } }
    )
    return response.data
  },

  /**
   * Create a new chat session
   * POST /api/chat/new
   */
  async createSession(data?: CreateSessionRequest): Promise<ApiResponse<ChatSession>> {
    const response = await apiClient.post<ApiResponse<ChatSession>>(
      '/api/chat/new',
      data || {}
    )
    return response.data
  },

  /**
   * Get session with messages
   * GET /api/chat/:sessionId
   */
  async getSession(sessionId: number): Promise<ApiResponse<ChatSessionDetail>> {
    const response = await apiClient.get<ApiResponse<ChatSessionDetail>>(
      `/api/chat/${sessionId}`
    )
    return response.data
  },

  /**
   * Update session title
   * PUT /api/chat/:sessionId
   */
  async updateSession(sessionId: number, title: string): Promise<ApiResponse<ChatSession>> {
    const response = await apiClient.put<ApiResponse<ChatSession>>(
      `/api/chat/${sessionId}`,
      { title }
    )
    return response.data
  },

  /**
   * Delete a chat session
   * DELETE /api/chat/:sessionId
   */
  async deleteSession(sessionId: number): Promise<ApiResponse<null>> {
    const response = await apiClient.delete<ApiResponse<null>>(
      `/api/chat/${sessionId}`
    )
    return response.data
  },

  /**
   * Send a message to a session
   * POST /api/chat/:sessionId/message
   */
  async sendMessage(
    sessionId: number, 
    data: SendMessageRequest
  ): Promise<ApiResponse<ChatMessage>> {
    const response = await apiClient.post<ApiResponse<ChatMessage>>(
      `/api/chat/${sessionId}/message`,
      data
    )
    return response.data
  },

  /**
   * Send message with streaming response
   * POST /api/chat/:sessionId/stream
   */
  streamMessage(
    sessionId: number,
    data: SendMessageRequest,
    onChunk: (chunk: string) => void,
    onDone: (message: ChatMessage) => void,
    onError: (error: Error) => void
  ): () => void {
    const controller = new AbortController()
    
    fetch(`/api/chat/${sessionId}/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify(data),
      signal: controller.signal
    }).then(async response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }
      
      const decoder = new TextDecoder()
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              // Parse final message from accumulated content
              continue
            }
            try {
              const parsed = JSON.parse(data)
              if (parsed.content) {
                onChunk(parsed.content)
              }
              if (parsed.done && parsed.message) {
                onDone(parsed.message)
              }
            } catch {
              onChunk(data)
            }
          }
        }
      }
    }).catch(error => {
      if (error.name !== 'AbortError') {
        onError(error)
      }
    })
    
    return () => controller.abort()
  }
}
