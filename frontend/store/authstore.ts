import { create } from 'zustand'
import { User } from '@/lib/types'
import {
  setAccessToken,
  setRefreshToken,
  clearAllTokens,
  refreshAccessToken,
  getAccessToken,
} from '@/lib/auth'
import { login, register, getMe } from '@/lib/api'

interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  isAuthenticated: false,

  login: async (email, password) => {
    set({ isLoading: true })
    try {
      const tokens = await login({ email, password })
      setAccessToken(tokens.access_token)
      setRefreshToken(tokens.refresh_token)
      const user = await getMe()
      set({ user, isAuthenticated: true, isLoading: false })
    } catch (err) {
      set({ isLoading: false })
      throw err
    }
  },

  register: async (email, password) => {
    set({ isLoading: true })
    try {
      await register({ email, password })
      const tokens = await login({ email, password })
      setAccessToken(tokens.access_token)
      setRefreshToken(tokens.refresh_token)
      const user = await getMe()
      set({ user, isAuthenticated: true, isLoading: false })
    } catch (err) {
      set({ isLoading: false })
      throw err
    }
  },

  logout: () => {
    clearAllTokens()
    set({ user: null, isAuthenticated: false })
  },

  loadUser: async () => {
    try {
      if (!getAccessToken()) {
        await refreshAccessToken()
      }
      const user = await getMe()
      set({ user, isAuthenticated: true })
    } catch {
      const token = await refreshAccessToken()
      if (token) {
        try {
          const user = await getMe()
          set({ user, isAuthenticated: true })
          return
        } catch {
          // fall through
        }
      }
      set({ user: null, isAuthenticated: false })
    }
  },
}))