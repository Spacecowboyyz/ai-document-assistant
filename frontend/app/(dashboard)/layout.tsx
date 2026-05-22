'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Sidebar } from '@/components/dashboard/Sidebar'
import { useAuth } from '@/hooks/useAuth'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const { loadUser, isAuthenticated } = useAuth()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const init = async () => {
      await loadUser()
      setChecking(false)
    }
    init()
  }, [loadUser])

  useEffect(() => {
    if (!checking && !isAuthenticated) {
      router.replace('/login')
    }
  }, [checking, isAuthenticated, router])

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <LoadingSpinner />
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto pt-14 md:pt-0">{children}</main>
    </div>
  )
}
