'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { getDocuments } from '@/lib/api'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

export default function ChatPage() {
  const params = useParams()
  const docId = params.docId as string
  const [filename, setFilename] = useState<string | undefined>()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const docs = await getDocuments()
        const doc = docs.find((d) => d.doc_id === docId)
        setFilename(doc?.filename)
      } catch {
        setFilename(undefined)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [docId])

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  return <ChatWindow docId={docId} filename={filename} />
}
