'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, LogOut, Menu, X } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { ModelsStatusBadge } from './ModelsStatusBadge'
import { Button } from '@/components/ui/Button'

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  const navContent = (
    <>
      <div className="flex items-center gap-2 px-4 py-6">
        <FileText className="h-6 w-6 text-primary" />
        <span className="font-semibold text-text-primary">Doc Assistant</span>
      </div>

      <nav className="flex-1 px-3">
        <Link
          href="/dashboard"
          onClick={() => setMobileOpen(false)}
          className={`flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm transition-colors ${
            pathname.startsWith('/dashboard') && !pathname.startsWith('/chat')
              ? 'bg-primary/20 text-primary'
              : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary'
          }`}
        >
          <FileText className="h-4 w-4" />
          Documents
        </Link>
      </nav>

      <div className="border-t border-border p-4 space-y-3">
        <ModelsStatusBadge />
        {user && (
          <p className="truncate text-xs text-text-secondary" title={user.email}>
            {user.email}
          </p>
        )}
        <Button variant="ghost" className="w-full justify-start" onClick={handleLogout}>
          <LogOut className="h-4 w-4" />
          Sign out
        </Button>
      </div>
    </>
  )

  return (
    <>
      <button
        type="button"
        className="fixed left-4 top-4 z-40 rounded-lg border border-border bg-surface p-2 md:hidden"
        onClick={() => setMobileOpen(true)}
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-surface md:flex">
        {navContent}
      </aside>

      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 md:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-surface md:hidden"
            >
              <button
                type="button"
                className="absolute right-3 top-4 rounded-lg p-1 text-text-secondary hover:bg-surface-hover"
                onClick={() => setMobileOpen(false)}
                aria-label="Close menu"
              >
                <X className="h-5 w-5" />
              </button>
              {navContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
