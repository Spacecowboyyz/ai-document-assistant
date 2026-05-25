'use client'

import { useCallback, useRef, useState } from 'react'
import { isConnectionLostError, streamChat, syncChat } from '@/lib/api'
import { mapChatError } from '@/lib/errors'
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
  const [usedSyncFallback, setUsedSyncFallback] = useState(false)

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim() || isStreaming) return

      setError(null)
      setUsedSyncFallback(false)
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

      const chatRequest = { question: question.trim(), doc_id: docId }
      let shouldTrySyncFallback = false

      const applySyncResponse = (answer: string, sources: Source[]) => {
        setUsedSyncFallback(true)
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  content: answer,
                  isStreaming: false,
                  sources,
                }
              : msg
          )
        )
      }

      try {
        await streamChat(
          sessionIdRef.current,
          chatRequest,
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
          },
          (err) => {
            if (isConnectionLostError(err)) {
              shouldTrySyncFallback = true
            } else {
              setError(mapChatError(err))
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
            }
          }
        )

        if (shouldTrySyncFallback) {
          try {
            const { answer, sources } = await syncChat(
              sessionIdRef.current,
              chatRequest
            )
            applySyncResponse(answer, sources)
          } catch (fallbackErr) {
            setError(
              mapChatError(
                fallbackErr instanceof Error
                  ? fallbackErr.message
                  : 'Chat failed'
              )
            )
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
          }
        }
      } catch (err) {
        if (
          err instanceof Error &&
          isConnectionLostError(err.message)
        ) {
          try {
            const { answer, sources } = await syncChat(
              sessionIdRef.current,
              chatRequest
            )
            applySyncResponse(answer, sources)
          } catch (fallbackErr) {
            setError(
              mapChatError(
                fallbackErr instanceof Error
                  ? fallbackErr.message
                  : 'Chat failed'
              )
            )
          }
        } else {
          setError(
            mapChatError(
              err instanceof Error ? err.message : 'Connection error'
            )
          )
        }
      } finally {
        setIsStreaming(false)
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId && msg.isStreaming
              ? { ...msg, isStreaming: false }
              : msg
          )
        )
      }
    },
    [docId, isStreaming]
  )

  return {
    messages,
    isStreaming,
    error,
    usedSyncFallback,
    sendMessage,
  }
}
