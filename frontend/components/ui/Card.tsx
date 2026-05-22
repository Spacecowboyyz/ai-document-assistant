import { ReactNode } from 'react'

interface CardProps {
  title?: string
  footer?: ReactNode
  children: ReactNode
  className?: string
}

export function Card({ title, footer, children, className = '' }: CardProps) {
  return (
    <div
      className={`rounded-xl border border-border bg-surface p-6 shadow-lg ${className}`}
    >
      {title && (
        <h2 className="mb-4 text-xl font-semibold text-text-primary">{title}</h2>
      )}
      {children}
      {footer && <div className="mt-6 border-t border-border pt-4">{footer}</div>}
    </div>
  )
}
