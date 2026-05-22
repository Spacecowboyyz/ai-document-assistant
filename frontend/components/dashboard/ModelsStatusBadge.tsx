'use client'

import { useEffect, useState } from 'react'
import { getModelsStatus } from '@/lib/api'
import { ModelsStatus } from '@/lib/types'

export function ModelsStatusBadge() {
  const [status, setStatus] = useState<ModelsStatus | null>(null)

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await getModelsStatus()
        setStatus(data)
      } catch {
        setStatus({
          ollama: 'offline',
          chat_model: '',
          embed_model: '',
          models_ready: false,
        })
      }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  if (!status) {
    return (
      <div className="h-6 w-24 animate-pulse rounded-full bg-surface-hover" />
    )
  }

  let label = 'AI offline'
  let colorClass = 'bg-error/20 text-error border-error/30'

  if (status.ollama === 'online' && status.models_ready) {
    label = 'AI ready'
    colorClass = 'bg-success/20 text-success border-success/30'
  } else if (status.ollama === 'online') {
    label = 'Models loading'
    colorClass = 'bg-warning/20 text-warning border-warning/30'
  }

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${colorClass}`}
      title={
        status.ollama === 'online'
          ? `${status.chat_model} / ${status.embed_model}`
          : 'Start Ollama: ollama serve'
      }
    >
      <span
        className={`mr-1.5 h-1.5 w-1.5 rounded-full ${
          status.models_ready
            ? 'bg-success'
            : status.ollama === 'online'
              ? 'bg-warning'
              : 'bg-error'
        }`}
      />
      {label}
    </span>
  )
}
