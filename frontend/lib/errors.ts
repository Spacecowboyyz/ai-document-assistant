export function parseApiError(detail: unknown, fallback = 'Something went wrong'): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && 'msg' in item) {
          return String((item as { msg: string }).msg)
        }
        return fallback
      })
      .join('. ')
  }
  return fallback
}

export async function parseResponseError(
  response: Response,
  fallback = 'Request failed'
): Promise<string> {
  try {
    const body = await response.json()
    return parseApiError(body.detail, fallback)
  } catch {
    return fallback
  }
}

export function mapHttpError(status: number, detail: string): string {
  if (status === 401) {
    return 'Your session expired. Please log in again.'
  }
  if (status === 429) {
    return (
      detail ||
      'AI rate limit reached (Groq free tier). Please wait a moment and try again.'
    )
  }
  if (status === 503) {
    return detail || 'AI service is temporarily unavailable.'
  }
  if (status >= 500) {
    return 'The server encountered an error. Please try again later.'
  }
  return detail
}

export function mapNetworkError(context: string): string {
  return `Cannot reach the backend (${context}). Ensure the API is running and NEXT_PUBLIC_API_URL is set correctly.`
}

export function mapUploadError(err: unknown): string {
  if (err instanceof TypeError) {
    return mapNetworkError('upload')
  }
  if (err instanceof Error) {
    const msg = err.message
    if (msg.includes('Session expired') || msg.includes('Not authenticated')) {
      return 'Your session expired. Please log in again.'
    }
    if (msg.toLowerCase().includes('rate limit')) {
      return msg
    }
    if (msg.toLowerCase().includes('unavailable') || msg.includes('503')) {
      return 'Document processing failed: AI service is unavailable. Try again in a moment.'
    }
    return msg
  }
  return 'Upload failed. Please try again.'
}

export function mapChatError(message: string): string {
  if (message.includes('Failed to fetch') || message.includes('NetworkError')) {
    return mapNetworkError('chat stream')
  }
  if (message.toLowerCase().includes('session expired')) {
    return 'Your session expired. Please log in again.'
  }
  if (message.toLowerCase().includes('rate limit')) {
    return message
  }
  return message
}
