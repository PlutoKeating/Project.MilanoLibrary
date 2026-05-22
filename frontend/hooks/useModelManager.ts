import { useState, useEffect, useCallback, useRef } from 'react'
import { getApiBaseUrl } from '~/lib/api'
import type { LocalModel } from '~/lib/types'

export type ModelType = 'online' | 'local'

export interface ModelStatus {
  status: 'not_installed' | 'downloading' | 'installed' | 'completed' | 'failed'
  progress: number
  error: string | null
}

export function useModelManager() {
  const [models, setModels] = useState<LocalModel[]>([])
  const [statusMap, setStatusMap] = useState<Record<string, ModelStatus>>({})
  const pollRef = useRef<Record<string, number>>({})

  const fetchModels = useCallback(async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/models/local`)
      if (!res.ok) return
      const data = await res.json()
      setModels(data.models || [])
    } catch {
      // ignore
    }
  }, [])

  const fetchStatus = useCallback(async (modelName: string) => {
    const requestedAt = new Date().toISOString()
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/models/local/${modelName}/status`)
      if (!res.ok) {
        console.log(`[model-download-status] ${requestedAt} ${modelName}: request failed`, {
          httpStatus: res.status,
        })
        return undefined
      }
      const data = await res.json()
      const status: ModelStatus = {
        status: data.status,
        progress: data.progress ?? 0,
        error: data.error ?? null,
      }
      console.log(`[model-download-status] ${requestedAt} ${modelName}: backend progress=${status.progress}%`, status)
      setStatusMap((prev) => ({
        ...prev,
        [modelName]: status,
      }))
      return data.status as string
    } catch (e: any) {
      console.log(`[model-download-status] ${requestedAt} ${modelName}: request error`, e?.message ?? e)
      return undefined
    }
  }, [])

  const stopPolling = useCallback((modelName: string) => {
    if (pollRef.current[modelName]) {
      window.clearInterval(pollRef.current[modelName])
      delete pollRef.current[modelName]
    }
  }, [])

  const startPolling = useCallback(
    (modelName: string) => {
      stopPolling(modelName)
      pollRef.current[modelName] = window.setInterval(async () => {
        const status = await fetchStatus(modelName)
        if (status === 'completed' || status === 'installed' || status === 'failed') {
          stopPolling(modelName)
          await fetchModels()
        }
      }, 1000)
    },
    [fetchStatus, fetchModels, stopPolling],
  )

  const startDownload = useCallback(
    async (modelName: string) => {
      setStatusMap((prev) => ({
        ...prev,
        [modelName]: { status: 'downloading', progress: 0, error: null },
      }))
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/models/local/${modelName}/download`, {
          method: 'POST',
        })
        if (!res.ok) {
          const text = await res.text()
          setStatusMap((prev) => ({
            ...prev,
            [modelName]: { status: 'failed', progress: 0, error: text },
          }))
          return
        }
      } catch (e: any) {
        setStatusMap((prev) => ({
          ...prev,
          [modelName]: { status: 'failed', progress: 0, error: e.message },
        }))
        return
      }

      startPolling(modelName)
    },
    [startPolling],
  )

  // Initial load: fetch models then check for in-progress downloads
  useEffect(() => {
    const init = async () => {
      await fetchModels()
    }
    init()
  }, [fetchModels])

  // After models are loaded, query each model's status to resume polling
  useEffect(() => {
    const resumePolling = async () => {
      for (const m of models) {
        if (m.installed) continue
        const status = await fetchStatus(m.name)
        if (status === 'downloading') {
          startPolling(m.name)
        }
      }
    }
    if (models.length > 0) {
      resumePolling()
    }
  }, [models, fetchStatus, startPolling])

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(pollRef.current).forEach((id) => window.clearInterval(id))
    }
  }, [])

  return {
    models,
    statusMap,
    fetchModels,
    startDownload,
  }
}
