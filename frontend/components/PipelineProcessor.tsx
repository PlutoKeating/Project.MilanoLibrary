import React, { useRef, useState } from 'react'
import { useForm, SubmitHandler } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useSummarize } from '../hooks/useSummarize'
import { useModelManager } from '../hooks/useModelManager'
import { TimelineProgress } from './TimelineProgress'
import { ModelSelector } from './ModelSelector'
import { PromptOptions } from './PromptOptions'
import { SubmitButton } from './SubmitButton'
import { AdapterManager } from './AdapterManager'
import { VideoService } from '../lib/types'
import { DEFAULT_LANGUAGE } from '../utils/constants/language'
import { videoConfigSchema, VideoConfigSchema } from '../utils/schemas/video'

interface PipelineProcessorProps {
  bookId: string | null
  onBeforeProcess?: () => Promise<string>
  onMetadataUpdate?: (metadata: { title?: string; author?: string; description?: string }) => void
  onSuccess?: () => Promise<void>
  titleText?: string
}

export function PipelineProcessor({
  bookId: propBookId,
  onBeforeProcess,
  onMetadataUpdate,
  onSuccess,
  titleText = '// PIPELINE COMPILER //',
}: PipelineProcessorProps) {
  const { register, handleSubmit, getValues, watch, setValue } = useForm<VideoConfigSchema>({
    defaultValues: {
      enableStream: true,
      model: '',
      showTimestamp: false,
      showEmoji: true,
      outputLanguage: DEFAULT_LANGUAGE,
      useStructuredOutput: true,
      respectChapters: true,
      modelType: 'online',
      localModel: 'small',
    },
    resolver: zodResolver(videoConfigSchema),
  })

  const [currentVideoUrl, setCurrentVideoUrl] = useState('')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [selectedAdapterId, setSelectedAdapterId] = useState('bilibili')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { loading, summary, taskStatus, activeTaskId, summarize, uploadAndSummarize, pollExistingTask } = useSummarize()
  const { models, statusMap, startDownload } = useModelManager()

  // Check for active task on mount or bookId change
  React.useEffect(() => {
    let cleanup: (() => void) | null = null

    const checkActiveTask = async () => {
      if (!propBookId) return

      try {
        const getApiBaseUrl = () => {
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

        const res = await fetch(`${getApiBaseUrl()}/api/status/${propBookId}`)
        if (res.ok) {
          const data = await res.json()
          const allDone = data.steps?.every(
            (step: any) => step.status === 'completed' || step.status === 'failed'
          )
          if (!allDone && data.task_id) {
            cleanup = pollExistingTask(data.task_id)
          }
        }
      } catch (err) {
        console.error('Error checking active task:', err)
      }
    }

    checkActiveTask()

    return () => {
      if (cleanup) {
        cleanup()
      }
    }
  }, [propBookId, pollExistingTask])

  // Track task metadata changes to update parent page
  React.useEffect(() => {
    if (taskStatus && onMetadataUpdate) {
      onMetadataUpdate({
        title: taskStatus.title || undefined,
        author: taskStatus.author || undefined,
        description: taskStatus.description || undefined,
      })
    }
  }, [taskStatus, onMetadataUpdate])

  // Trigger onSuccess when completed
  React.useEffect(() => {
    if (taskStatus) {
      const allDone = taskStatus.steps?.every(
        (step) => step.status === 'completed' || step.status === 'failed'
      )
      const hasCompleted = taskStatus.steps?.some((step) => step.status === 'completed')
      
      if (allDone && hasCompleted && onSuccess) {
        onSuccess()
      }
    }
  }, [taskStatus, onSuccess])

  const onFormSubmit: SubmitHandler<VideoConfigSchema> = async () => {
    try {
      let activeBookId = propBookId
      if (!activeBookId && onBeforeProcess) {
        activeBookId = await onBeforeProcess()
      }

      if (!activeBookId) {
        alert('BOOK CONTAINER NOT INITIALIZED')
        return
      }

      const formValues = getValues()
      const userKey = window.localStorage.getItem('user-openai-apikey') ? JSON.parse(window.localStorage.getItem('user-openai-apikey') || '""') : ''
      const userBaseUrl = window.localStorage.getItem('user-openai-base-url') ? JSON.parse(window.localStorage.getItem('user-openai-base-url') || '""') : ''
      const userModelName = window.localStorage.getItem('user-openai-model') ? JSON.parse(window.localStorage.getItem('user-openai-model') || '""') : ''

      const videoConfigPayload = {
        ...formValues,
        book_id: activeBookId,
      }

      if (uploadFile) {
        await uploadAndSummarize(
          uploadFile,
          { service: VideoService.LocalVideo, ...videoConfigPayload },
          { userKey, baseUrl: userBaseUrl, modelName: userModelName, shouldShowTimestamp: formValues.showTimestamp }
        )
      } else {
        if (!currentVideoUrl) {
          alert('INPUT URL OR CHOOSE LOCAL FILE')
          return
        }
        await summarize(
          { videoId: currentVideoUrl, service: selectedAdapterId, ...videoConfigPayload },
          { userKey, baseUrl: userBaseUrl, modelName: userModelName, shouldShowTimestamp: formValues.showTimestamp }
        )
      }
    } catch (err: any) {
      alert(`COMPILATION PIPELINE ERROR: ${err.message || err}`)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    setUploadFile(file)
  }

  const handleRemoveFile = () => {
    setUploadFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const hasSucceeded = !!taskStatus && taskStatus.steps?.length > 0 && taskStatus.steps?.every(
    (step) => step.status === 'completed'
  )

  const isPipelineActive = !!activeTaskId && (!taskStatus || !taskStatus.steps?.every(
    (step) => step.status === 'completed' || step.status === 'failed'
  ))

  const showForm = !loading && !isPipelineActive && !hasSucceeded

  return (
    <div className="border border-slate-800 bg-slate-950 p-4 font-mono text-xs text-cyan-100">
      <div className="border-b border-slate-900 pb-2 mb-4">
        <span className="text-cyan-400 font-bold uppercase tracking-widest">{titleText}</span>
      </div>

      {showForm ? (
        <>
          <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4">
            <div className="flex flex-col">
              <label className="text-slate-500 text-[10px] mb-1 font-bold uppercase">视频链接 (Video Link URL)</label>
              <input
                type="text"
                placeholder="输入哔哩哔哩或 YouTube 视频链接..."
                value={currentVideoUrl}
                onChange={(e) => setCurrentVideoUrl(e.target.value)}
                disabled={!!uploadFile || loading}
                className="border border-slate-800 bg-slate-950 px-3 py-2 text-cyan-100 outline-none focus:border-cyan-500 disabled:opacity-50"
              />
            </div>

            <AdapterManager selectedAdapterId={selectedAdapterId} onSelectAdapter={setSelectedAdapterId} />

            <div className="mt-2">
              {!uploadFile ? (
                <label className="flex cursor-pointer items-center justify-center border border-dashed border-slate-800 bg-slate-950 hover:border-cyan-500 hover:text-cyan-400 px-4 py-4 text-center">
                  <span>或 上传本地视频文件</span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    onChange={handleFileChange}
                    disabled={loading}
                    className="hidden"
                  />
                </label>
              ) : (
                <div className="flex items-center justify-between border border-slate-800 bg-slate-950 px-4 py-2">
                  <span className="text-cyan-100 font-bold">{uploadFile.name}</span>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    disabled={loading}
                    className="text-fuchsia-400 hover:text-fuchsia-300 disabled:opacity-50"
                  >
                    移除
                  </button>
                </div>
              )}
            </div>

            <ModelSelector
              modelType={watch('modelType') || 'online'}
              selectedLocalModel={watch('localModel') || 'small'}
              models={models}
              statusMap={statusMap}
              onModelTypeChange={(type) => setValue('modelType', type)}
              onLocalModelChange={(name) => setValue('localModel', name)}
              onDownload={startDownload}
            />

            <PromptOptions getValues={getValues} register={register} />

            <div className="pt-2">
              <SubmitButton loading={loading} />
            </div>
          </form>
          {activeTaskId && <TimelineProgress taskStatus={taskStatus} taskId={activeTaskId} />}
        </>
      ) : (
        <TimelineProgress taskStatus={taskStatus} taskId={activeTaskId} />
      )}
    </div>
  )
}
