'use client'

import { useCallback, useRef, useState } from 'react'
import { streamChat } from '@/lib/api'
import { ChatMessage, Source } from '@/lib/types'

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function useChat(docId: string) {
  const sessionIdRef = useRef<string>(
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : generateId()
  )
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim() || isStreaming) return

      setError(null)
      const userMessage: ChatMessage = {
        id: generateId(),
        role: 'user',
        content: question.trim(),
      }
      const assistantId = generateId()
      const assistantPlaceholder: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        isStreaming: true,
      }

      setMessages((prev) => [...prev, userMessage, assistantPlaceholder])
      setIsStreaming(true)

      await streamChat(
        sessionIdRef.current,
        { question: question.trim(), doc_id: docId },
        (token) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? { ...msg, content: msg.content + token }
                : msg
            )
          )
        },
        (sources: Source[]) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? {
                    ...msg,
                    isStreaming: false,
                    sources,
                  }
                : msg
            )
          )
          setIsStreaming(false)
        },
        (err) => {
          setError(err)
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? {
                    ...msg,
                    content: msg.content || 'Failed to get a response.',
                    isStreaming: false,
                  }
                : msg
            )
          )
          setIsStreaming(false)
        }
      )
    },
    [docId, isStreaming]
  )

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
  }
}
