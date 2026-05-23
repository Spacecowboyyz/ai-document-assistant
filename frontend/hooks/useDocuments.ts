'use client'

import { useCallback, useEffect, useState } from 'react'
import { getDocuments, uploadDocument, deleteDocument } from '@/lib/api'
import { DocumentInfo } from '@/lib/types'
import { mapNetworkError, mapUploadError } from '@/lib/errors'

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const docs = await getDocuments()
      setDocuments(docs)
    } catch (err) {
      setError(
        err instanceof TypeError
          ? mapNetworkError('documents')
          : err instanceof Error
            ? err.message
            : 'Failed to load documents'
      )
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refetch()
  }, [refetch])

  const upload = async (file: File) => {
    setIsUploading(true)
    setError(null)
    try {
      await uploadDocument(file)
      await refetch()
    } catch (err) {
      setError(mapUploadError(err))
      throw err
    } finally {
      setIsUploading(false)
    }
  }

  const remove = async (docId: string) => {
    setError(null)
    try {
      await deleteDocument(docId)
      await refetch()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document')
      throw err
    }
  }

  return {
    documents,
    isLoading,
    isUploading,
    error,
    refetch,
    upload,
    remove,
  }
}
