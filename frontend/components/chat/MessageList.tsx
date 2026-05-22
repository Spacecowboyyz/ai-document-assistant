'use client'

import { useEffect, useRef } from 'react'
import { MessageSquare } from 'lucide-react'
import { ChatMessage } from '@/lib/types'
import { MessageBubble } from './MessageBubble'

interface MessageListProps {
  messages: ChatMessage[]
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <MessageSquare className="h-12 w-12 text-text-secondary/40" />
        <p className="mt-4 text-lg font-medium text-text-primary">
          Ask a question about this document
        </p>
        <p className="mt-2 max-w-sm text-sm text-text-secondary">
          Answers stream from your local AI and include citations when available.
        </p>
      </div>
    )
  }

  return (
    <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
