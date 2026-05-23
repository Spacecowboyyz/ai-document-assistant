let accessToken: string | null = null

const REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60 // 7 days
const ACCESS_TOKEN_KEY = 'access_token'
const TOKEN_EXPIRY_BUFFER_SEC = 60

let refreshInFlight: Promise<string | null> | null = null

function setRefreshCookie(token: string) {
  if (typeof document === 'undefined') return
  document.cookie = `refresh_token=${encodeURIComponent(token)}; path=/; max-age=${REFRESH_COOKIE_MAX_AGE}; samesite=lax`
}

function clearRefreshCookie() {
  if (typeof document === 'undefined') return
  document.cookie = 'refresh_token=; path=/; max-age=0; samesite=lax'
}

export function isAccessTokenExpired(token: string, bufferSeconds = TOKEN_EXPIRY_BUFFER_SEC): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    if (typeof payload.exp !== 'number') return true
    return payload.exp * 1000 <= Date.now() + bufferSeconds * 1000
  } catch {
    return true
  }
}

/** Drop stale sessionStorage token on load and whenever read. */
function getValidStoredAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  const stored = sessionStorage.getItem(ACCESS_TOKEN_KEY)
  if (!stored) return null
  if (isAccessTokenExpired(stored)) {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY)
    return null
  }
  return stored
}

if (typeof window !== 'undefined') {
  getValidStoredAccessToken()
}

export function setAccessToken(token: string) {
  accessToken = token
  if (typeof window !== 'undefined') {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, token)
  }
}

export function getAccessToken(): string | null {
  if (accessToken) {
    if (isAccessTokenExpired(accessToken)) {
      clearAccessToken()
    } else {
      return accessToken
    }
  }

  const stored = getValidStoredAccessToken()
  if (stored) {
    accessToken = stored
    return stored
  }

  return null
}

export function clearAccessToken() {
  accessToken = null
  if (typeof window !== 'undefined') {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  }
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

function redirectToLogin(): void {
  if (typeof window === 'undefined') return
  const path = window.location.pathname
  if (path.startsWith('/login') || path.startsWith('/register')) return
  window.location.href = '/login'
}

async function performRefresh(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    clearAllTokens()
    return null
  }

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
  if (!data.access_token || !data.refresh_token) {
    clearAllTokens()
    return null
  }

  setAccessToken(data.access_token)
  setRefreshToken(data.refresh_token)
  return data.access_token
}

export async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight

  refreshInFlight = performRefresh().finally(() => {
    refreshInFlight = null
  })

  return refreshInFlight
}

/**
 * Returns a valid access token, refreshing if missing/expired.
 * Clears invalid session tokens and redirects to login when refresh fails.
 */
export async function ensureAccessToken(): Promise<string | null> {
  const current = getAccessToken()
  if (current && !isAccessTokenExpired(current)) {
    return current
  }

  if (current) {
    clearAccessToken()
  }

  const refreshed = await refreshAccessToken()
  if (refreshed && !isAccessTokenExpired(refreshed)) {
    return refreshed
  }

  clearAllTokens()
  redirectToLogin()
  return null
}
