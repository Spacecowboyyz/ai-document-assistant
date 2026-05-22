import { ReactNode } from 'react'

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">
          AI Document Assistant
        </h1>
        <p className="mt-2 text-sm text-text-secondary">
          Chat with your documents using local AI
        </p>
      </div>
      <div className="w-full max-w-md">{children}</div>
    </div>
  )
}
