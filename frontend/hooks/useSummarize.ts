import { useState, useCallback, useRef } from 'react'

function getApiBaseUrl() {
  if (typeof window !== 'undefined') {
    const stored = window.localStorage.getItem('backend-base-url')
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        if (parsed) {
          return typeof parsed === 'string' ? parsed.replace(/\/$/, '') : parsed
        }
      } catch (e) {
        return stored
      }
    }
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
}

function parseBackendErrorMessage(message: string) {
  const matcher = message.match(/^(\d{3})::([\s\S]*)$/)
  if (!matcher) {
    return { statusCode: 0, detail: message }
  }
  return {
    statusCode: Number(matcher[1]),
    detail: matcher[2].trim(),
  }
}

export interface TaskStep {
  id: string
  title: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused' | 'cancelled' | 'stopped'
  progress: number
  message: string
}

export interface TaskStatus {
  task_id: string
  flow_type: 'url' | 'local'
  last_updated: number
  steps: TaskStep[]
  is_paused?: boolean
  is_stopped?: boolean
  title?: string
  author?: string
  description?: string
}

export function useSummarize() {
  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState('')
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const resetSummary = useCallback(() => {
    setSummary('')
    setTaskStatus(null)
    setActiveTaskId(null)
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
  }, [])

  const _readStream = useCallback(async (response: Response) => {
    if (!response.body) {
      const data = await response.json()
      setSummary(data.result || '')
      return
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullText = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      fullText += chunk
      setSummary(fullText)
    }
  }, [])

  const summarize = useCallback(async (videoConfig: any, userConfig: any) => {
    setLoading(true)
    setSummary('')
    setTaskStatus(null)

    const abortController = new AbortController()
    abortRef.current = abortController

    const taskId = videoConfig.videoId.replace(/[^a-zA-Z0-9_-]/g, '_')
    setActiveTaskId(taskId)

    let pollInterval: any = null

    const pollStatus = async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/status/${taskId}`)
        if (res.ok) {
          const data = await res.json()
          setTaskStatus(data)
        }
      } catch (err) {
        // Silently ignore polling errors
      }
    }

    try {
      // Convert camelCase to snake_case for backend compatibility
      const snakeCaseVideoConfig = {
        video_id: videoConfig.videoId,
        task_id: taskId,
        book_id: videoConfig.book_id || videoConfig.bookId,
        service: videoConfig.service,
        page_number: videoConfig.pageNumber,
        enable_stream: videoConfig.enableStream,
        model: videoConfig.model,
        show_timestamp: videoConfig.showTimestamp,
        show_emoji: videoConfig.showEmoji,
        output_language: videoConfig.outputLanguage,
        use_structured_output: videoConfig.useStructuredOutput,
        respect_chapters: videoConfig.respectChapters,
        model_type: videoConfig.modelType,
        local_model: videoConfig.localModel,
      }
      const snakeCaseUserConfig = userConfig
        ? {
            user_key: userConfig.userKey,
            base_url: userConfig.baseUrl,
            model_name: userConfig.modelName,
            should_show_timestamp: userConfig.shouldShowTimestamp,
          }
        : null

      // Start polling
      pollStatus()
      pollInterval = setInterval(pollStatus, 800)

      const response = await fetch(`${getApiBaseUrl()}/api/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_config: snakeCaseVideoConfig, user_config: snakeCaseUserConfig }),
        signal: abortController.signal,
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(`${response.status}::${text || 'Unknown error'}`)
      }

      const contentType = response.headers.get('content-type') || ''
      if (contentType.includes('text/plain') && response.body) {
        await _readStream(response)
      } else {
        const data = await response.json()
        const text = data.result || ''
        setSummary(text)
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        return
      }
      const { statusCode, detail } = parseBackendErrorMessage(error.message || 'Unknown error')
      if (statusCode === 501) {
        setSummary('❌ 该视频没有字幕，或视频太短。')
      } else {
        setSummary(`❌ 请求出错: ${detail || error.message}`)
      }
    } finally {
      setLoading(false)
      abortRef.current = null
      if (pollInterval) {
        clearInterval(pollInterval)
      }
      await pollStatus()
    }
  }, [_readStream])

  const uploadAndSummarize = useCallback(async (file: File, videoConfig: any, userConfig: any) => {
    setLoading(true)
    setSummary('')
    setTaskStatus(null)

    const abortController = new AbortController()
    abortRef.current = abortController

    const taskId = `${file.name}_${file.size}`.replace(/[^a-zA-Z0-9_-]/g, '_')
    setActiveTaskId(taskId)

    let pollInterval: any = null

    const pollStatus = async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/status/${taskId}`)
        if (res.ok) {
          const data = await res.json()
          setTaskStatus(data)
        }
      } catch (err) {
        // Silently ignore polling errors
      }
    }

    try {
      const snakeCaseVideoConfig = {
        video_id: videoConfig.videoId || '',
        task_id: taskId,
        book_id: videoConfig.book_id || videoConfig.bookId,
        service: videoConfig.service || 'local-video',
        page_number: videoConfig.pageNumber,
        enable_stream: videoConfig.enableStream,
        model: videoConfig.model,
        show_timestamp: videoConfig.showTimestamp,
        show_emoji: videoConfig.showEmoji,
        output_language: videoConfig.outputLanguage,
        use_structured_output: videoConfig.useStructuredOutput,
        respect_chapters: videoConfig.respectChapters,
        model_type: videoConfig.modelType,
        local_model: videoConfig.localModel,
      }
      const snakeCaseUserConfig = userConfig
        ? {
            user_key: userConfig.userKey,
            base_url: userConfig.baseUrl,
            model_name: userConfig.modelName,
            should_show_timestamp: userConfig.shouldShowTimestamp,
          }
        : null

      // Start polling
      pollStatus()
      pollInterval = setInterval(pollStatus, 800)

      const formData = new FormData()
      formData.append('video_config', JSON.stringify(snakeCaseVideoConfig))
      if (snakeCaseUserConfig) {
        formData.append('user_config', JSON.stringify(snakeCaseUserConfig))
      }
      formData.append('file', file)

      const response = await fetch(`${getApiBaseUrl()}/api/video/upload`, {
        method: 'POST',
        body: formData,
        signal: abortController.signal,
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(`${response.status}::${text || 'Unknown error'}`)
      }

      const contentType = response.headers.get('content-type') || ''
      if (contentType.includes('text/plain') && response.body) {
        await _readStream(response)
      } else {
        const data = await response.json()
        const text = data.result || ''
        setSummary(text)
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        return
      }
      const { statusCode, detail } = parseBackendErrorMessage(error.message || 'Unknown error')
      if (statusCode === 501) {
        setSummary('❌ 该视频没有字幕，或视频太短。')
      } else {
        setSummary(`❌ 请求出错: ${detail || error.message}`)
      }
    } finally {
      setLoading(false)
      abortRef.current = null
      if (pollInterval) {
        clearInterval(pollInterval)
      }
      await pollStatus()
    }
  }, [_readStream])

  const pollExistingTask = useCallback((taskId: string) => {
    setLoading(true)
    setActiveTaskId(taskId)

    let isCleared = false
    const pollStatus = async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/status/${taskId}`)
        if (res.ok) {
          const data = await res.json()
          if (isCleared) return true
          setTaskStatus(data)
          const allDone = data.steps?.every(
            (step: any) => step.status === 'completed' || step.status === 'failed'
          )
          if (allDone) {
            setLoading(false)
            return true
          }
        } else {
          if (isCleared) return true
          setLoading(false)
          return true
        }
      } catch (err) {
        // ignore
      }
      return false
    }

    pollStatus()
    const interval = setInterval(async () => {
      const done = await pollStatus()
      if (done) {
        clearInterval(interval)
      }
    }, 800)

    return () => {
      isCleared = true
      clearInterval(interval)
    }
  }, [])

  return { loading, summary, taskStatus, activeTaskId, resetSummary, summarize, uploadAndSummarize, pollExistingTask }
}
