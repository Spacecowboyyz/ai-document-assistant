'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload } from 'lucide-react'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

const MAX_SIZE = 50 * 1024 * 1024

interface UploadZoneProps {
  onUpload: (file: File) => Promise<void>
  isUploading: boolean
  error: string | null
}

export function UploadZone({ onUpload, isUploading, error }: UploadZoneProps) {
  const [localError, setLocalError] = useState<string | null>(null)

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setLocalError(null)
      const file = acceptedFiles[0]
      if (!file) return
      if (file.size > MAX_SIZE) {
        setLocalError('File must be under 50MB')
        return
      }
      try {
        await onUpload(file)
      } catch {
        // parent sets error
      }
    },
    [onUpload]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: isUploading,
  })

  const displayError = localError || error

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors hover:scale-[1.005] ${
          isDragActive
            ? 'border-accent bg-accent/5'
            : 'border-border bg-surface hover:border-primary/50'
        } ${isUploading ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-3">
          {isUploading ? (
            <LoadingSpinner />
          ) : (
            <Upload className="h-10 w-10 text-primary" />
          )}
          <div>
            <p className="font-medium text-text-primary">
              {isUploading
                ? 'Indexing document...'
                : isDragActive
                  ? 'Drop PDF here'
                  : 'Drag & drop a PDF, or click to browse'}
            </p>
            <p className="mt-1 text-sm text-text-secondary">PDF only, max 50MB</p>
          </div>
        </div>
      </div>
      {displayError && (
        <p className="rounded-lg bg-error/10 px-3 py-2 text-sm text-error whitespace-pre-wrap">
          {displayError}
        </p>
      )}
    </div>
  )
}
