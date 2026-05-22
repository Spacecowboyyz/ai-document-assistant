'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { ChatMessage } from '@/lib/types'
import { StreamingText } from './StreamingText'

interface MessageBubbleProps {
  message: ChatMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const isUser = message.role === 'user'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-primary text-white'
            : 'border border-border bg-surface text-text-primary'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : (
          <div className="text-sm">
            <StreamingText
              content={message.content || (message.isStreaming ? '' : 'No response')}
              isStreaming={message.isStreaming}
            />
          </div>
        )}

        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 border-t border-border pt-2">
            <button
              type="button"
              onClick={() => setSourcesOpen(!sourcesOpen)}
              className="flex w-full items-center gap-1 text-xs text-accent hover:underline"
            >
              {sourcesOpen ? (
                <ChevronUp className="h-3 w-3" />
              ) : (
                <ChevronDown className="h-3 w-3" />
              )}
              {message.sources.length} source
              {message.sources.length !== 1 ? 's' : ''}
            </button>
            {sourcesOpen && (
              <ul className="mt-2 space-y-2">
                {message.sources.map((src, i) => (
                  <li
                    key={i}
                    className="rounded-lg bg-background/50 p-2 text-xs text-text-secondary"
                  >
                    <span className="font-medium text-text-primary">
                      {src.source_filename} · p.{src.page_number}
                    </span>
                    <p className="mt-1 line-clamp-3">{src.content}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}
