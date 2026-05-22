let accessToken: string | null = null

const REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60 // 7 days

function setRefreshCookie(token: string) {
  if (typeof document === 'undefined') return
  document.cookie = `refresh_token=${encodeURIComponent(token)}; path=/; max-age=${REFRESH_COOKIE_MAX_AGE}; samesite=lax`
}

function clearRefreshCookie() {
  if (typeof document === 'undefined') return
  document.cookie = 'refresh_token=; path=/; max-age=0; samesite=lax'
}

export function setAccessToken(token: string) {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

export function clearAccessToken() {
  accessToken = null
}

export function setRefreshToken(token: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('refresh_token', token)
    setRefreshCookie(token)
  }
}

export function getRefreshToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('refresh_token')
  }
  return null
}

export function clearRefreshToken() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('refresh_token')
    clearRefreshCookie()
  }
}

export function clearAllTokens() {
  clearAccessToken()
  clearRefreshToken()
}

export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null

  const response = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })

  if (!response.ok) {
    clearAllTokens()
    return null
  }

  const data = await response.json()
  setAccessToken(data.access_token)
  setRefreshToken(data.refresh_token)
  return data.access_token
}
