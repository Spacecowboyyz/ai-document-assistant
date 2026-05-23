import {
  TokenResponse,
  User,
  DocumentInfo,
  UploadResponse,
  ModelsStatus,
  RegisterRequest,
  LoginRequest,
  ChatRequest,
  Source,
} from './types'
import { ensureAccessToken, clearAccessToken, clearAllTokens } from './auth'
import {
  mapChatError,
  mapHttpError,
  mapNetworkError,
  parseResponseError,
} from './errors'

/** Proxied through Next.js rewrites (JSON + multipart). */
const BASE_URL = '/api'

/**
 * Direct backend URL when NEXT_PUBLIC_API_URL is set.
 * Use for SSE and multipart upload — Next.js rewrites can fail on those bodies.
 * Set NEXT_PUBLIC_API_URL=http://localhost:8000 in .env.local
 */
function getDirectApiBase(): string {
  const direct = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '')
  return direct ? `${direct}/api` : BASE_URL
}

function getDirectApiUrl(path: string): string {
  const base = getDirectApiBase()
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${base}${normalizedPath}`
}

function buildAuthHeaders(token: string, options: RequestInit): Headers {
  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${token}`)
  if (options.body instanceof FormData) {
    headers.delete('Content-Type')
  }
  return headers
}

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = await ensureAccessToken()
  if (!token) {
    throw new Error('Not authenticated')
  }

  let response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: buildAuthHeaders(token, options),
  })

  if (response.status === 401) {
    clearAccessToken()
    const newToken = await ensureAccessToken()
    if (!newToken) {
      throw new Error('Session expired')
    }

    if (options.body instanceof FormData) {
      throw new Error('Session expired during request. Please try again.')
    }

    response = await fetch(`${BASE_URL}${url}`, {
      ...options,
      headers: buildAuthHeaders(newToken, options),
    })
  }

  return response
}

// Auth
export async function register(data: RegisterRequest): Promise<User> {
  const response = await fetch(`${BASE_URL}/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const detail = await parseResponseError(response, 'Registration failed')
    throw new Error(mapHttpError(response.status, detail))
  }
  return response.json()
}

export async function login(data: LoginRequest): Promise<TokenResponse> {
  const response = await fetch(`${BASE_URL}/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const detail = await parseResponseError(response, 'Login failed')
    throw new Error(mapHttpError(response.status, detail))
  }
  return response.json()
}

export async function getMe(): Promise<User> {
  const response = await fetchWithAuth('/v1/auth/me')
  if (!response.ok) throw new Error('Failed to get user')
  return response.json()
}

// Documents
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const token = await ensureAccessToken()
  if (!token) {
    throw new Error('Not authenticated')
  }

  const formData = new FormData()
  formData.append('file', file)

  // Bypass Next.js rewrite proxy (multipart can 500 inside Next with no backend logs)
  const response = await fetch(getDirectApiUrl('/v1/upload'), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  })

  if (!response.ok) {
    const detail = await parseResponseError(response, 'Upload failed')
    throw new Error(mapHttpError(response.status, detail))
  }

  return response.json()
}

export async function getDocuments(): Promise<DocumentInfo[]> {
  const response = await fetchWithAuth('/v1/documents')
  if (!response.ok) throw new Error('Failed to fetch documents')
  return response.json()
}

export async function deleteDocument(docId: string): Promise<void> {
  const response = await fetchWithAuth(`/v1/documents/${docId}`, {
    method: 'DELETE',
  })
  if (!response.ok) throw new Error('Failed to delete document')
}

// Models status
export async function getModelsStatus(): Promise<ModelsStatus> {
  try {
    const response = await fetch(`${BASE_URL}/v1/models/status`)
    if (!response.ok) {
      return {
        ai_provider: 'ollama',
        ollama: 'offline',
        chat_model: '',
        embed_model: '',
        models_ready: false,
      }
    }
    return response.json()
  } catch {
    return {
      ai_provider: 'ollama',
      ollama: 'offline',
      chat_model: '',
      embed_model: '',
      models_ready: false,
    }
  }
}

function parseSseLine(
  line: string,
  onToken: (token: string) => void,
  onDone: (sources: Source[]) => void
): boolean {
  const trimmed = line.replace(/\r$/, '').trim()
  if (!trimmed.startsWith('data:')) return false

  const jsonStr = trimmed.slice(5).trim()
  if (!jsonStr) return false

  try {
    const parsed = JSON.parse(jsonStr)
    if (parsed.done) {
      onDone(parsed.sources || [])
      return true
    }
    if (parsed.token) {
      onToken(parsed.token)
    }
  } catch {
    // skip malformed chunk
  }
  return false
}

function processSseBuffer(
  buffer: string,
  onToken: (token: string) => void,
  onDone: (sources: Source[]) => void
): string {
  const normalized = buffer.replace(/\r\n/g, '\n')
  const lines = normalized.split('\n')
  const remainder = lines.pop() ?? ''

  for (const line of lines) {
    if (parseSseLine(line, onToken, onDone)) {
      return ''
    }
  }
  return remainder
}

async function processSseStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onToken: (token: string) => void,
  onDone: (sources: Source[]) => void
): Promise<boolean> {
  const decoder = new TextDecoder()
  let buffer = ''
  let receivedDone = false

  const handleDone = (sources: Source[]) => {
    receivedDone = true
    onDone(sources)
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    buffer = processSseBuffer(buffer, onToken, handleDone)
    if (receivedDone) {
      await reader.cancel().catch(() => {})
      return true
    }
  }

  buffer += decoder.decode()
  if (buffer) {
    processSseBuffer(buffer, onToken, handleDone)
    if (!receivedDone && buffer.trim()) {
      parseSseLine(buffer, onToken, handleDone)
    }
  }

  return receivedDone
}

// Chat SSE — direct backend URL; token fetched immediately before each request
export async function streamChat(
  sessionId: string,
  data: ChatRequest,
  onToken: (token: string) => void,
  onDone: (sources: Source[]) => void,
  onError: (error: string) => void
): Promise<void> {
  const streamBase = getDirectApiBase()
  const path = `/v1/chat/${sessionId}`
  const body = JSON.stringify(data)

  try {
    let token = await ensureAccessToken()
    if (!token) {
      onError('Session expired. Please log in again.')
      return
    }

    let response = await fetch(`${streamBase}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        Accept: 'text/event-stream',
      },
      body,
      cache: 'no-store',
    })

    if (response.status === 401) {
      clearAccessToken()
      clearAllTokens()
      token = await ensureAccessToken()
      if (!token) {
        onError('Session expired. Please log in again.')
        return
      }
      response = await fetch(`${streamBase}${path}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          Accept: 'text/event-stream',
        },
        body,
        cache: 'no-store',
      })
    }

    if (!response.ok) {
      const detail = await parseResponseError(response, 'Chat failed')
      onError(mapHttpError(response.status, detail))
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      onError('No response body')
      return
    }

    const receivedDone = await processSseStream(reader, onToken, onDone)
    if (!receivedDone) {
      onError('Connection lost before the response finished. Please try again.')
      return
    }
  } catch (err) {
    if (err instanceof TypeError) {
      onError(mapNetworkError('chat stream'))
      return
    }
    const message = err instanceof Error ? err.message : 'Connection error'
    onError(mapChatError(message))
  }
}
