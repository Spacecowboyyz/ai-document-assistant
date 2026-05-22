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
import {
  getAccessToken,
  setAccessToken,
  getRefreshToken,
  clearAllTokens,
  setRefreshToken,
  refreshAccessToken,
} from './auth'
import { parseApiError, parseResponseError } from './errors'

const BASE_URL = '/api'

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getAccessToken()
  const headers: HeadersInit = {
    ...options.headers,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }

  let response = await fetch(`${BASE_URL}${url}`, { ...options, headers })

  if (response.status === 401) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      const retryHeaders: HeadersInit = {
        ...options.headers,
        Authorization: `Bearer ${newToken}`,
      }
      response = await fetch(`${BASE_URL}${url}`, { ...options, headers: retryHeaders })
    } else if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
  }

  return response
}

async function getAuthHeaders(): Promise<HeadersInit> {
  let token = getAccessToken()
  if (!token) {
    token = await refreshAccessToken()
  }
  if (!token) {
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
    throw new Error('Not authenticated')
  }
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }
}

// Auth
export async function register(data: RegisterRequest): Promise<User> {
  const response = await fetch(`${BASE_URL}/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    throw new Error(await parseResponseError(response, 'Registration failed'))
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
    throw new Error(await parseResponseError(response, 'Login failed'))
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
  const formData = new FormData()
  formData.append('file', file)
  const response = await fetchWithAuth('/v1/upload', {
    method: 'POST',
    body: formData,
  })
  if (!response.ok) {
    throw new Error(await parseResponseError(response, 'Upload failed'))
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
  const response = await fetch(`${BASE_URL}/v1/models/status`)
  if (!response.ok) throw new Error('Failed to get models status')
  return response.json()
}

async function processSseStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onToken: (token: string) => void,
  onDone: (sources: Source[]) => void
): Promise<void> {
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
        const jsonStr = line.slice(6).trim()
        if (!jsonStr) continue
        try {
          const parsed = JSON.parse(jsonStr)
          if (parsed.done) {
            onDone(parsed.sources || [])
          } else {
            onToken(parsed.token || '')
          }
        } catch {
          // skip malformed lines
        }
      }
    }
  }
}

// Chat SSE
export async function streamChat(
  sessionId: string,
  data: ChatRequest,
  onToken: (token: string) => void,
  onDone: (sources: Source[]) => void,
  onError: (error: string) => void
): Promise<void> {
  try {
    let headers = await getAuthHeaders()
    let response = await fetch(`${BASE_URL}/v1/chat/${sessionId}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    })

    if (response.status === 401) {
      const newToken = await refreshAccessToken()
      if (!newToken) {
        onError('Session expired. Please log in again.')
        if (typeof window !== 'undefined') window.location.href = '/login'
        return
      }
      headers = await getAuthHeaders()
      response = await fetch(`${BASE_URL}/v1/chat/${sessionId}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
      })
    }

    if (!response.ok) {
      const message = await parseResponseError(response, 'Chat failed')
      onError(message)
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      onError('No response body')
      return
    }

    await processSseStream(reader, onToken, onDone)
  } catch (err) {
    onError(err instanceof Error ? err.message : 'Connection error')
  }
}
