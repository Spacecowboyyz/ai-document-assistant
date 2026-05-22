'use client'

import { useDocuments } from '@/hooks/useDocuments'
import { UploadZone } from '@/components/dashboard/UploadZone'
import { DocumentList } from '@/components/dashboard/DocumentList'

export default function DashboardPage() {
  const { documents, isLoading, isUploading, error, upload, remove } = useDocuments()

  return (
    <div className="mx-auto max-w-4xl p-4 md:p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary">Your documents</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Upload PDFs and chat with them using local AI
        </p>
      </header>

      <section className="mb-8">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-text-secondary">
          Upload
        </h2>
        <UploadZone onUpload={upload} isUploading={isUploading} error={error} />
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-text-secondary">
          Library
        </h2>
        <DocumentList documents={documents} isLoading={isLoading} onDelete={remove} />
      </section>
    </div>
  )
}
