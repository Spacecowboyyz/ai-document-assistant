'use client'

import { motion } from 'framer-motion'

interface StreamingTextProps {
  content: string
  isStreaming?: boolean
}

export function StreamingText({ content, isStreaming }: StreamingTextProps) {
  return (
    <motion.span
      key={content.length}
      initial={isStreaming ? { opacity: 0.7 } : false}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.15 }}
      className="whitespace-pre-wrap"
    >
      {content}
      {isStreaming && (
        <motion.span
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ repeat: Infinity, duration: 1 }}
          className="ml-0.5 inline-block h-4 w-0.5 align-middle bg-accent"
        />
      )}
    </motion.span>
  )
}
