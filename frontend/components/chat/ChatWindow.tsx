'use client'

import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { useChat } from '@/hooks/useChat'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'

interface ChatWindowProps {
  docId: string
  filename?: string
}

export function ChatWindow({ docId, filename }: ChatWindowProps) {
  const { messages, isStreaming, error, sendMessage } = useChat(docId)

  return (
    <div className="flex h-[calc(100vh-0px)] flex-col md:h-screen">
      <header className="flex items-center gap-3 border-b border-border bg-surface px-4 py-3">
        <Link
          href="/dashboard"
          className="rounded-lg p-1.5 text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-primary"
          aria-label="Back to dashboard"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-semibold text-text-primary">
            {filename || 'Document chat'}
          </h1>
          <p className="truncate text-xs text-text-secondary">ID: {docId}</p>
        </div>
      </header>

      {error && (
        <div className="mx-4 mt-4 rounded-lg bg-error/10 px-3 py-2 text-sm text-error whitespace-pre-wrap">
          {error}
        </div>
      )}

      <MessageList messages={messages} />
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  )
}
