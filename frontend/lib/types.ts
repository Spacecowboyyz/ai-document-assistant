export interface User {
  user_id: string
  email: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface DocumentInfo {
  doc_id: string
  filename: string
  chunk_count: number
  created_at: string
}

export interface UploadResponse {
  doc_id: string
  filename: string
  chunk_count: number
  message: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  isStreaming?: boolean
}

export interface Source {
  page_number: number
  source_filename: string
  content: string
}

export interface ModelsStatus {
  ai_provider?: 'ollama' | 'groq'
  ollama: 'online' | 'offline'
  chat_model: string
  embed_model: string
  models_ready: boolean
}

export interface RegisterRequest {
  email: string
  password: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface ChatRequest {
  question: string
  doc_id: string
}