'use client'

import { useAuthStore } from '@/store/authstore'

export function useAuth() {
  const user = useAuthStore((s) => s.user)
  const isLoading = useAuthStore((s) => s.isLoading)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const login = useAuthStore((s) => s.login)
  const register = useAuthStore((s) => s.register)
  const logout = useAuthStore((s) => s.logout)
  const loadUser = useAuthStore((s) => s.loadUser)

  return {
    user,
    isLoading,
    isAuthenticated,
    login,
    register,
    logout,
    loadUser,
  }
}
