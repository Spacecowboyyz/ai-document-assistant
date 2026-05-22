'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/Button'

export default function AuthError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-6 text-center">
      <h2 className="text-lg font-semibold text-text-primary">Something went wrong</h2>
      <p className="mt-2 text-sm text-text-secondary">{error.message}</p>
      <div className="mt-4 flex justify-center gap-3">
        <Button onClick={reset}>Try again</Button>
        <Link href="/login">
          <Button variant="secondary">Sign in</Button>
        </Link>
      </div>
    </div>
  )
}
