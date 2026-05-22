'use client'

import { useState } from 'react'
import { FileText } from 'lucide-react'
import { DocumentInfo } from '@/lib/types'
import { DocumentCard } from './DocumentCard'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

interface DocumentListProps {
  documents: DocumentInfo[]
  isLoading: boolean
  onDelete: (docId: string) => Promise<void>
}

export function DocumentList({ documents, isLoading, onDelete }: DocumentListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner />
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-surface/50 py-16 text-center">
        <FileText className="h-12 w-12 text-text-secondary/50" />
        <h3 className="mt-4 text-lg font-medium text-text-primary">No documents yet</h3>
        <p className="mt-2 max-w-sm text-sm text-text-secondary">
          Upload a PDF above to index it and start chatting with your content.
        </p>
      </div>
    )
  }

  const handleDelete = async (docId: string) => {
    setDeletingId(docId)
    try {
      await onDelete(docId)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-3">
      {documents.map((doc) => (
        <DocumentCard
          key={doc.doc_id}
          document={doc}
          onDelete={handleDelete}
          isDeleting={deletingId === doc.doc_id}
        />
      ))}
    </div>
  )
}
