'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { MessageSquare, Trash2 } from 'lucide-react'
import { DocumentInfo } from '@/lib/types'
import { Button } from '@/components/ui/Button'

interface DocumentCardProps {
  document: DocumentInfo
  onDelete: (docId: string) => Promise<void>
  isDeleting?: boolean
}

export function DocumentCard({ document, onDelete, isDeleting }: DocumentCardProps) {
  const created = new Date(document.created_at).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-4 rounded-xl border border-border bg-surface p-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="min-w-0 flex-1">
        <h3 className="truncate font-medium text-text-primary">{document.filename}</h3>
        <p className="mt-1 text-sm text-text-secondary">
          {document.chunk_count} chunks · {created}
        </p>
      </div>
      <div className="flex shrink-0 gap-2">
        <Link href={`/chat/${document.doc_id}`}>
          <Button variant="primary" className="gap-1.5">
            <MessageSquare className="h-4 w-4" />
            Chat
          </Button>
        </Link>
        <Button
          variant="danger"
          loading={isDeleting}
          onClick={() => onDelete(document.doc_id)}
          aria-label={`Delete ${document.filename}`}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </motion.div>
  )
}
