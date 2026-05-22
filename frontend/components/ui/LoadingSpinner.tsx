'use client'

export function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' }) {
  const sizeClass = size === 'sm' ? 'h-4 w-4' : 'h-5 w-5'
  return (
    <span
      className={`inline-block ${sizeClass} animate-spin rounded-full border-2 border-accent border-t-transparent`}
      role="status"
      aria-label="Loading"
    />
  )
}
